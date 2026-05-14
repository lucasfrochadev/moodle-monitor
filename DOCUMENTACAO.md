# Moodle Monitor — Documentação Técnica

Sistema autônomo que monitora atividades acadêmicas no Moodle da UNISALESIANO
(`missaosalesiana.mrooms.net`) e notifica o aluno quando algo muda (nova atividade,
prazo alterado, arquivo adicionado, etc.).

---

## Índice

1. [Arquitetura Geral](#1-arquitetura-geral)
2. [Fluxo de Autenticação (2 domínios)](#2-fluxo-de-autenticação)
3. [Extração de Dados do Moodle](#3-extração-de-dados)
4. [Detecção de Mudanças](#4-detecção-de-mudanças)
5. [Pipeline de Processamento](#5-pipeline)
6. [Armazenamento (SQLite)](#6-armazenamento)
7. [Notificações](#7-notificações)
8. [Configuração](#8-configuração)
9. [Como dar Manutenção](#9-manutenção)

---

## 1. Arquitetura Geral

```
main.py
  │
  └─ MonitorEngine (src/monitor/engine.py)
       │
       ├─ SessionManager (portal)  ── httpx.Client ── unisalesiano.com.br
       ├─ SessionManager (moodle)  ── httpx.Client ── missaosalesiana.mrooms.net
       │
       ├─ AuthManager (src/auth/moodle_auth.py)
       │    │
       │    ├─ 1. POST validarLogin.php (portal)
       │    ├─ 2. POST loginAva.php → extrai credenciais Moodle
       │    └─ 3. POST login/index.php + token.php (Moodle)
       │
       ├─ Extractor (src/scraper/extractor.py)
       │    │
       │    ├─ API (MoodleAPIClient) → /webservice/rest/server.php
       │    └─ HTML (MoodleHTMLParser) → BeautifulSoup + lxml
       │
       ├─ Pipeline (src/pipeline/pipeline.py)
       │    │
       │    ├─ CourseScanStage   → descobre cursos
       │    ├─ SectionScanStage  → descobre seções e atividades
       │    ├─ ActivityDetailStage → detalhes de cada atividade
       │    ├─ SnapshotStage     → gera hash e salva estado
       │    ├─ CompareStage      → detecta mudanças
       │    └─ NotificationStage → envia alertas
       │
       ├─ Database (SQLite + migrations)
       └─ Notificadores (Email / Telegram / Discord)
```

### Diagrama de Fluxo de Dados

```
PORTAL (unisalesiano.com.br)
  │
  │  POST /salaEstudo/libs/soa/validarLogin.php  (RA + senha + campus)
  │  Resposta: [{"tipo":"OK","url":"menu.php"}]
  │
  ▼
  │  POST /salaEstudo/libs/soa/loginAva.php
  │  Resposta: HTML com <form> contendo username + password do Moodle
  │
  ▼
MOODLE (missaosalesiana.mrooms.net)
  │
  │  POST /login/index.php (com as credenciais extraídas)
  │  → Cookie MoodleSession estabelecido
  │
  │  POST /login/token.php (mesmas credenciais)
  │  → Token de API
  │
  ▼
EXTRAÇÃO
  │
  │  GET /my/ → dashboard → descobre cursos (via select dropdown)
  │  GET /course/view.php?id=X → seções e atividades
  │  GET /mod/assign/view.php?id=X → detalhes (descrição, data, arquivos)
  │
  ▼
COMPARAÇÃO
  │
  │  Gera SHA-256 do conteúdo de cada atividade
  │  Compara com o último snapshot salvo no SQLite
  │  Se hash mudou → detecta quais campos mudaram
  │
  ▼
NOTIFICAÇÃO
  │
  └─ Email SMTP (ou Telegram / Discord)
```

---

## 2. Fluxo de Autenticação

### O Problema

O sistema precisa acessar DOIS sites diferentes:

1. **Portal UNISALESIANO** (`unisalesiano.com.br`) — onde o aluno faz login com RA e senha
2. **Moodle AVA** (`missaosalesiana.mrooms.net`) — onde as atividades estão

O Moodle NÃO aceita login direto com RA/senha do portal. Em vez disso, o portal
gera automaticamente um **par de credenciais temporárias** (username + password)
que funcionam no Moodle. É como se o portal "criasse" uma conta para você no
Moodle na hora.

### Como descobrimos isso?

Analisando o JavaScript do portal (`menu.js`), encontramos:

```javascript
// Arquivo original: ../libs/js/menu.js (linha ~85)
function loginDiversos(string) {
    var form = $('<form></form>')
        .attr("method", "post")
        .attr("action", "../libs/soa/" + string + ".php");
    form.appendTo('body').submit();
}
```

Quando o usuário clica no botão "AVA AMBIENTE VIRTUAL", a função é chamada como
`loginDiversos('loginAva')`, que faz um POST para `../libs/soa/loginAva.php`.

### Etapa 1: Login no Portal

Arquivo: `src/auth/moodle_auth.py` — método `_login_portal()`

```python
def _login_portal(self) -> None:
    """Login no portal com RA + senha + unidade."""

    login_data = {
        "ra": self._username,        # ex: "221226"
        "senha": self._password,      # a senha do portal
    }
    if self._campus_id:
        login_data["idCasa"] = self._campus_id  # "12" (Lins) ou "13" (Araçatuba)

    # Faz POST para o endpoint AJAX do portal
    response = self._portal_session.request(
        "POST",
        "../libs/soa/validarLogin.php",  # URL relativa → resolve para absoluta
        data=login_data,
    )

    # Resposta esperada em caso de sucesso:
    # [{"tipo": "OK", "url": "menu.php"}]

    # Resposta em caso de erro:
    # [{"tipo": "NEGADO", "mensagem": "SENHA INCORRETA!"}]

    json_response = response.json()
    if json_response[0]["tipo"] != "OK":
        raise AuthenticationError(f"Login negado: {json_response[0].get('mensagem')}")
```

**Como as URLs relativas funcionam?**

O `SessionManager` tem uma URL base configurada:
```python
base_url = "https://unisalesiano.com.br/salaEstudo/alunos/"
```

Quando passamos `"../libs/soa/validarLogin.php"`, o método `resolve_url()` faz:
```python
from urllib.parse import urljoin
urljoin("https://unisalesiano.com.br/salaEstudo/alunos/",
        "../libs/soa/validarLogin.php")
# Resultado: https://unisalesiano.com.br/salaEstudo/libs/soa/validarLogin.php
```

### Etapa 2: Extrair Credenciais do Moodle

Arquivo: `src/auth/moodle_auth.py` — método `_get_moodle_credentials()`

```python
def _get_moodle_credentials(self) -> tuple[str, str]:
    """Faz POST para loginAva.php e extrai username + password do HTML."""

    response = self._portal_session.request(
        "POST",
        "../libs/soa/loginAva.php",  # usa a MESMA sessão do portal (cookies)
        data={},
    )

    # O HTML retornado é algo como:
    # <html>
    #   <form id="frmBB" method="post"
    #         action="https://missaosalesiana.mrooms.net/login/index.php">
    #     <input type="hidden" name="username" value="13221226"/>
    #     <input type="hidden" name="password" value="2HA#21LU"/>
    #   </form>
    #   <script>document.getElementById('frmBB').submit();</script>
    # </html>

    soup = BeautifulSoup(response.text, "lxml")
    form = soup.find("form", id="frmBB")

    # Extrai os valores dos campos ocultos
    username = form.find("input", {"name": "username"}).get("value", "")
    password = form.find("input", {"name": "password"}).get("value", "")

    return username, password
```

**Por que `BeautifulSoup`?** — O servidor retorna HTML, não JSON. Usamos
BeautifulSoup para "parsear" o HTML e extrair os campos do formulário, da mesma
forma que um navegador faria.

### Etapa 3: Login no Moodle

Arquivo: `src/auth/moodle_auth.py` — método `_try_direct_moodle_login()`

```python
def _try_direct_moodle_login(self) -> bool:
    """Loga no Moodle com as credenciais extraídas."""

    # Primeiro faz GET na página de login para extrair o "logintoken"
    # (um token CSRF que o Moodle exige)
    login_page = self._moodle_session.request("GET", "/login/index.php")

    logintoken = self._extract_login_token(login_page.text)
    login_data = {
        "username": self._moodle_username,   # ex: "13221226"
        "password": self._moodle_password,   # ex: "2HA#21LU"
    }
    if logintoken:
        login_data["logintoken"] = logintoken  # token CSRF

    # Faz POST no formulário de login
    response = self._moodle_session.request("POST", "/login/index.php", data=login_data)

    # Se o cookie MoodleSession foi definido, o login funcionou
    if self._moodle_session.get_cookie("MoodleSession"):
        logger.info("Login direto no Moodle bem-sucedido")
        return True

    return False
```

### Etapa 4: Obter Token da API

Mesmo após o login direto, também obtemos um token da API REST do Moodle:

```python
def _try_moodle_token_auth(self) -> bool:
    """Obtém token para a API REST do Moodle."""

    response = self._moodle_session.request("POST", "/login/token.php", data={
        "username": self._moodle_username,
        "password": self._moodle_password,
        "service": "moodle_mobile_app",  # serviço que tem permissões de leitura
    })

    data = response.json()
    if "token" in data:
        self._moodle_session.state.token = data["token"]
        # O token parece algo como: "2aafa0cb41b8806c426f75219906fd04"
        return True
```

### Por que duas sessions separadas?

```python
# Cada domínio tem seu próprio SessionManager com cookies independentes
self._portal_session = SessionManager(base_url="https://unisalesiano.com.br/salaEstudo/alunos/")
self._moodle_session = SessionManager(base_url="https://missaosalesiana.mrooms.net/")
```

São dois sites diferentes (domínios diferentes), cada um com seus próprios
cookies de sessão. O `SessionManager` mantém um `httpx.Client` separado para
cada um, com seu próprio "jar" de cookies.

---

## 3. Extração de Dados

### 3.1 Descoberta de Cursos

Arquivo: `src/scraper/extractor.py` — método `_extract_courses_html()`

Quando a API REST não retorna cursos (como acontece neste Moodle), o sistema
usa HTML scraping. O desafio foi que os cursos não aparecem como links, mas sim
como opções de um `<select>` (dropdown) no dashboard:

```python
def _extract_courses_html(self) -> list[CourseData]:
    # Passo 1: Busca o dashboard
    response = self._session.request("GET", "/my/")

    # Passo 2: Tenta encontrar links do tipo /course/view.php?id=XXX
    course_ids = set()
    for match in re.finditer(r'/course/view\.php\?id=(\d+)', response.text):
        course_ids.add(int(match.group(1)))

    # Passo 3: Fallback — busca no catálogo de cursos
    if not course_ids:
        resp = self._session.request("GET", "/course/index.php")
        for match in re.finditer(r'/course/view\.php\?id=(\d+)', resp.text):
            course_ids.add(int(match.group(1)))

    # Passo 4: Fallback final — dropdown de calendário
    if not course_ids:
        soup = BeautifulSoup(response.text, "lxml")
        course_select = soup.find("select", id="calendar-course-filter-1")
        if course_select:
            for opt in course_select.find_all("option"):
                val = opt.get("value", "")
                if val and val.isdigit() and int(val) > 1:
                    course_ids.add(int(val))
                # Opção com value="1" é "Todos os cursos" — ignoramos

    # Passo 5: Para cada ID, busca a página do curso
    courses = []
    for cid in course_ids:
        course_resp = self._session.request("GET", f"/course/view.php?id={cid}")
        parsed = self._html.parse_course_page(course_resp.text, cid)
        if parsed:
            courses.append(parsed)

    return courses
```

### 3.2 Parsing de Páginas HTML

Arquivo: `src/scraper/html_parser.py`

O parser usa **seletores CSS estáveis** do Moodle para encontrar elementos:

```python
class MoodleHTMLParser:
    # Seletores que funcionam no Moodle 3.x até 4.x
    COURSE_SECTION_SELECTOR = "li.section"        # cada tópico do curso
    ACTIVITY_SELECTOR = "li.activity"              # cada atividade
    ACTIVITY_INSTANCE_SELECTOR = "div.activityinstance"  # container da atividade
    INSTANCE_NAME_SELECTOR = "span.instancename"   # nome da atividade
    SECTION_NAME_SELECTOR = "h3.sectionname"       # nome do tópico
```

Exemplo de como uma atividade é extraída:

```python
def _parse_single_activity(self, element: Tag) -> Optional[ActivityData]:
    # Encontra o container da atividade
    instance_el = element.select_one("div.activityinstance")
    link_el = instance_el.find("a")

    # Extrai o nome
    name_el = link_el.select_one("span.instancename")
    name = name_el.get_text(strip=True)

    # Extrai a URL e o ID (cmid)
    href = link_el.get("href", "")
    cmid = self._extract_cmid_from_url(href)  # ex: ?id=12345 → 12345

    # Detecta o tipo (assign, quiz, forum, resource, etc.)
    mod_classes = element.get("class", [])
    activity_type = self._detect_type_from_classes(mod_classes)

    return ActivityData(
        cmid=cmid or 0,
        type=activity_type,   # ex: ActivityType.ASSIGN
        name=name,
        url=str(href),        # ex: /mod/assign/view.php?id=12345
    )
```

**Detecção de tipo de atividade:**

O Moodle coloca classes CSS nos elementos `li.activity` que indicam o tipo:

```python
def _detect_type_from_classes(self, classes) -> ActivityType:
    class_str = " ".join(str(c) for c in classes) if classes else ""
    for at in ActivityType:
        if at.value in class_str:  # ex: "assign" em "assign modtype_assign"
            return at
    return ActivityType.UNKNOWN
```

Tipos suportados: `assign` (trabalho), `quiz` (prova), `forum`, `resource` (arquivo),
`page`, `url`, `folder`, `lesson`, `choice`, `feedback`, `glossary`, `wiki`, `workshop`.

### 3.3 Extração de Detalhes

Para cada atividade, o sistema busca a página individual para obter detalhes:

```python
def _extract_activity_detail_html(self, activity: ActivityData) -> Optional[ActivityData]:
    # Busca a página individual da atividade
    response = self._session.request("GET", activity.url)

    # Parseia a página
    parsed = self._html.parse_activity_page(response.text, activity.cmid)

    if parsed:
        # O parse_activity_page extrai:
        # - descrição (texto da atividade)
        # - data de entrega (due_date)
        # - data de abertura (open_date)
        # - arquivos anexados (files)
        return parsed

    return activity  # fallback: retorna os dados básicos
```

**Extração de datas:**

```python
def _extract_due_date(self, soup: BeautifulSoup) -> Optional[datetime]:
    # Procura textos como "Data de entrega", "Due date", "Vencimento"
    texts = ["Data de entrega", "Due date", "Vencimento", "Prazo final"]
    return self._find_date_after_text(soup, texts)

def _find_date_after_text(self, soup, label_texts):
    # Para cada label, procura no HTML e extrai a data ao lado
    for text in label_texts:
        pattern = re.compile(re.escape(text), re.IGNORECASE)
        for element in soup.find_all(string=pattern):
            parent = element.parent
            next_text = parent.find_next(string=True)
            # Extrai datas no formato: dd/mm/aaaa hh:mm
            dates = self._extract_dates(str(next_text))
            if dates:
                return dates[0]
```

**Extração de arquivos:**

```python
def _extract_files(self, soup: BeautifulSoup) -> list[MoodleFile]:
    files = []
    # Links para arquivos do Moodle (sempre contêm "pluginfile.php")
    for link in soup.find_all("a", href=re.compile(r"pluginfile.php", re.I)):
        href = link.get("href", "")
        filename = link.get_text(strip=True) or href.split("/")[-1]
        files.append(MoodleFile(filename=filename, file_url=str(href)))

    return files
```

---

## 4. Detecção de Mudanças

### 4.1 Hashing SHA-256

Arquivo: `src/detector/hasher.py`

Em vez de comparar strings diretamente (o que geraria falsos positivos por
pequenas diferenças de formatação), o sistema gera um **hash SHA-256 do
conteúdo normalizado**:

```python
class ContentHasher:
    @staticmethod
    def compute_full_hash(activity: ActivityData) -> str:
        hasher = hashlib.sha256()

        # Nome (normalizado: sem espaços extras, minúsculas)
        hasher.update(self._normalize_text(activity.name).encode("utf-8"))
        hasher.update(b"|")

        # Descrição (HTML limpo: sem scripts, styles, tags)
        if activity.description:
            normalized_desc = self._normalize_html(activity.description)
            hasher.update(normalized_desc.encode("utf-8"))
        hasher.update(b"|")

        # Datas
        hasher.update(self._date_str(activity.due_date).encode("utf-8"))
        hasher.update(b"|")

        # Nota máxima
        grade = str(activity.max_grade or "") or ""
        hasher.update(grade.encode("utf-8"))
        hasher.update(b"|")

        # Arquivos (hash combinado de todos os arquivos)
        files_hash = self.compute_files_hash(activity.files)
        hasher.update(files_hash.encode("utf-8"))

        return hasher.hexdigest()
```

**Normalização de HTML** — remove variações irrelevantes:

```python
@staticmethod
def _normalize_html(html: str) -> str:
    # Remove scripts e estilos
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)

    # Remove tags HTML
    text = re.sub(r"<[^>]+>", " ", text)

    # Remove atributos dinâmicos (data-*)
    text = re.sub(r"data-[a-zA-Z_-]+=\"[^\"]*\"", "", text)

    # Normaliza espaços e minúsculas
    text = re.sub(r"\s+", " ", text)
    text = text.strip().lower()
    return text
```

### 4.2 Comparação

Arquivo: `src/pipeline/stages.py` — classe `CompareStage`

```python
async def execute(self, ctx: StageContext) -> StageContext:
    for course_id, activities in ctx.activities_by_course.items():
        for activity in activities:
            activity_id = db_activity["id"]

            # Busca o último snapshot salvo
            last_snapshot = self._snapshot_repo.get_latest_by_activity(activity_id)

            # PASSO CRÍTICO: compara o hash primeiro!
            # Se o hash é o mesmo, o conteúdo não mudou → pula
            snap = dict(last_snapshot)
            if snap["full_hash"] == ContentHasher.compute_full_hash(activity):
                continue  # nada mudou

            # Se o hash mudou, faz a comparação campo a campo
            old_activity = self._snapshot_to_activity(last_snapshot)
            changes = Comparator.compare(
                old_activity=old_activity,
                new_activity=activity,
                ...
            )
```

### 4.3 Filtro de Falsos Positivos

Arquivo: `src/detector/filter.py`

```python
class FalsePositiveFilter:
    def __init__(self, cooldown_minutes: int = 30, min_diff_chars: int = 3):
        self._cooldown = timedelta(minutes=cooldown_minutes)
        self._min_diff = min_diff_chars

    def filter_changes(self, changes, last_notified):
        filtered = []
        for change in changes:
            # Ignora mudanças muito pequenas (ex: 1 caractere diferente)
            if change.diff and len(change.diff) < self._min_diff:
                continue

            # Respeita o cooldown (não notifica a mesma atividade várias vezes)
            last = last_notified.get((change.activity_id, change.change_type))
            if last and (datetime.now() - last) < self._cooldown:
                continue

            filtered.append(change)
        return filtered
```

---

## 5. Pipeline

Arquivo: `src/pipeline/pipeline.py`

O pipeline executa 6 estágios em sequência, cada um recebendo e modificando um
`StageContext`:

```python
class StageContext:
    courses: list[CourseData]
    sections_by_course: dict[str, list[SectionData]]
    activities_by_course: dict[str, list[ActivityData]]
    snapshots_created: dict[str, str]  # activity_id → snapshot_id
    changes_detected: list[DetectedChange]
```

### Estágio 1: CourseScanStage

```python
class CourseScanStage:
    def execute(self, ctx):
        courses = extractor.extract_courses()

        # Filtra apenas os cursos configurados (course_ids no config.yaml)
        if self._course_ids:
            courses = [c for c in courses if c.course_id in self._course_ids]

        for course in courses:
            course_repo.upsert(course)  # salva no banco

        ctx.courses = courses
        return ctx
```

### Estágio 2: SectionScanStage

Para cada curso, acessa a página e extrai seções (tópicos) e as atividades
dentro de cada seção. Usa `asyncio.Semaphore` para controlar concorrência
(máximo 5 cursos simultâneos).

### Estágio 3: ActivityDetailStage

Para cada atividade já descoberta, busca a página individual para obter
descrição completa, data de entrega, arquivos anexados, etc.

### Estágio 4: SnapshotStage

Gera o hash SHA-256 do estado atual da atividade e salva como um novo snapshot
no banco (com versionamento).

### Estágio 5: CompareStage

Compara o snapshot atual com o anterior usando hash. Se mudou, detecta
especificamente o que mudou (nome, descrição, prazo, arquivos, nota).

### Estágio 6: NotificationStage

Para cada mudança detectada que passou pelo filtro, envia notificação para
todos os canais configurados (email, Telegram, Discord).

---

## 6. Armazenamento

Arquivo: `src/storage/database.py`

Banco SQLite com WAL mode (Write-Ahead Logging) para performance:

```python
class Database:
    def __init__(self, path: str):
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row  # retorna linhas como dict-like
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
```

### Principais Tabelas

```sql
-- Cursos descobertos
CREATE TABLE courses (
    id TEXT PRIMARY KEY,          -- UUID
    course_id INTEGER UNIQUE,     -- ID do Moodle
    fullname TEXT NOT NULL,
    shortname TEXT
);

-- Atividades
CREATE TABLE activities (
    id TEXT PRIMARY KEY,
    course_id TEXT REFERENCES courses(id),
    cmid INTEGER NOT NULL,        -- "course module id" do Moodle
    type TEXT NOT NULL,
    name TEXT NOT NULL
);

-- Snapshots (estado de uma atividade em um momento)
CREATE TABLE activity_snapshots (
    id TEXT PRIMARY KEY,
    activity_id TEXT REFERENCES activities(id),
    version INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    due_date TIMESTAMP,
    full_hash TEXT NOT NULL,       -- SHA-256 do conteúdo completo
    taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Arquivos (extraídos de cada atividade)
CREATE TABLE activity_files (
    id TEXT PRIMARY KEY,
    activity_id TEXT REFERENCES activities(id),
    snapshot_id TEXT REFERENCES activity_snapshots(id),
    filename TEXT NOT NULL,
    file_url TEXT
);

-- Mudanças detectadas
CREATE TABLE detected_changes (
    id TEXT PRIMARY KEY,
    activity_id TEXT REFERENCES activities(id),
    change_type TEXT NOT NULL,     -- "new_activity", "deadline_change", etc.
    old_value TEXT,
    new_value TEXT,
    severity TEXT,
    notified BOOLEAN DEFAULT FALSE
);
```

**Atenção:** `sqlite3.Row` suporta acesso por chave (`row["nome"]`) mas NÃO
suporta `.get()`. Para usar `.get()`, converta com `dict(row)`:

```python
row = cur.fetchone()           # sqlite3.Row
nome = row["name"]             # funciona
nome = row.get("name", "")     # ERRO! sqlite3.Row não tem .get()
d = dict(row)                  # converte para dict
nome = d.get("name", "")       # funciona
```

---

## 7. Notificações

### Email SMTP

Arquivo: `src/notifier/email.py`

```python
class EmailNotifier(Notifier):
    async def send(self, change, activity_name, course_name, activity_url):
        subject = f"[Moodle Monitor] Nova atividade - {activity_name}"
        html = self._build_html(subject, message)

        msg = MIMEText(html, "html")
        msg["Subject"] = subject
        msg["From"] = self._from
        msg["To"] = self._to

        # Envio assíncrono (roda SMTP em uma thread separada)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._send_sync, msg)

    def _send_sync(self, msg):
        server = smtplib.SMTP(self._server, self._port)
        server.starttls()              # TLS na porta 587
        server.login(self._username, self._password)
        server.send_message(msg)
```

### Adicionar um Novo Canal (ex: WhatsApp)

Crie uma classe que herda de `Notifier` (definido em `src/notifier/base.py`):

```python
from src.notifier.base import Notifier

class WhatsAppNotifier(Notifier):
    @property
    def name(self) -> str:
        return "whatsapp"

    async def send(self, change, activity_name, course_name, activity_url):
        # Sua lógica de envio aqui
        return True

    async def health_check(self) -> bool:
        return True
```

Depois registre no `engine.py` no método `_init_notifiers()`.

---

## 8. Configuração

### config.yaml

```yaml
portal:
  url: "${PORTAL_URL}"           # resolvido via variável de ambiente
  username: "${PORTAL_USERNAME}"
  password: "${PORTAL_PASSWORD}"
  campus_id: "${PORTAL_CAMPUS_ID}"

moodle:
  url: "${MOODLE_URL}"

monitoring:
  check_interval_minutes: 15     # a cada 15 min
  max_concurrent_courses: 5      # 5 cursos paralelos
  course_ids:                    # só monitora esses cursos
    - 16090   # ARQUITETURA DE COMPUTADORES
    - 16057   # BANCO DE DADOS I

notifications:
  email:
    enabled: true
    smtp_server: "${SMTP_SERVER}"
    smtp_port: 587
    smtp_username: "${SMTP_USERNAME}"
    smtp_password: "${SMTP_PASSWORD}"
    from_address: "${SMTP_USERNAME}"
    to_address: "${NOTIFICATION_EMAIL}"
    use_tls: true
```

### .env (NÃO VERSIONAR!)

```
PORTAL_URL=https://unisalesiano.com.br/salaEstudo/alunos/
PORTAL_USERNAME=221226
PORTAL_PASSWORD=minhasenha
PORTAL_CAMPUS_ID=13

MOODLE_URL=https://missaosalesiana.mrooms.net/

SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=meuemail@gmail.com
SMTP_PASSWORD=senhaapp
NOTIFICATION_EMAIL=meuemail@hotmail.com
```

### Resolução de Variáveis

Arquivo: `src/config/settings.py`

O sistema resolve `${VARIAVEL}` no YAML usando variáveis de ambiente:

```python
def _resolve_env(value: Any) -> Any:
    if isinstance(value, str):
        pattern = re.compile(r"\$\{([^}]+)\}")
        return pattern.sub(lambda m: os.environ.get(m.group(1), ""), value)
    return value
```

---

## 9. Manutenção

### 9.1 Como adicionar um novo tipo de atividade

No arquivo `src/scraper/models.py`, adicione ao enum:

```python
class ActivityType(StrEnum):
    ASSIGN = "assign"
    QUIZ = "quiz"
    # ...
    H5P = "h5p"  # novo tipo
```

Se o Moodle renderizar de forma diferente, pode precisar de um parser específico
em `html_parser.py`.

### 9.2 Como adicionar um novo seletor CSS

Se o tema do Moodle mudar e os seletores pararem de funcionar:

```python
# Em html_parser.py, atualize os seletores
COURSE_SECTION_SELECTOR = "li.section"        # se mudar para div.section
ACTIVITY_SELECTOR = "li.activity"             # se mudar para div.activity
```

### 9.3 Como debugar

**Testar autenticação isoladamente:**

```python
# Script rápido para testar auth
from src.auth.session import SessionManager
from src.auth.moodle_auth import AuthManager

portal = SessionManager(base_url="https://unisalesiano.com.br/salaEstudo/alunos/", ...)
moodle = SessionManager(base_url="https://missaosalesiana.mrooms.net/", ...)

auth = AuthManager(portal, moodle, username="221226", password="...", campus_id="13")
auth.authenticate()

print(f"MoodleSession: {moodle.get_cookie('MoodleSession')}")
print(f"Token: {moodle.state.token}")
```

**Ver o que o HTML retorna:**

```python
from bs4 import BeautifulSoup
response = session.request("GET", "/my/")
with open("debug.html", "w", encoding="utf-8") as f:
    f.write(response.text)
# Depois abre debug.html no navegador
```

**Ver o banco diretamente:**

```bash
sqlite3 data/monitor.db
.tables
SELECT fullname, course_id FROM courses;
```

(Se `sqlite3` não estiver instalado, use Python:
`python -c "import sqlite3; c=sqlite3.connect('data/monitor.db');
cur=c.execute('SELECT fullname FROM courses');
[print(r[0]) for r in cur.fetchall()]"`)

### 9.4 Reset total

```bash
# Para começar do zero (apaga TODOS os dados)
Remove-Item -Recurse -Force data/
```

### 9.5 Estrutura de Diretórios

```
moodle-monitor/
├── main.py                    # Ponto de entrada
├── config.yaml                # Configuração (versionar!)
├── .env                       # Credenciais (NÃO versionar!)
├── DOCUMENTACAO.md            # Este documento
│
├── src/
│   ├── auth/
│   │   ├── session.py         # HTTP client com cookies e retry
│   │   └── moodle_auth.py     # Autenticação em 2 estágios
│   │
│   ├── scraper/
│   │   ├── extractor.py       # Estratégia híbrida API + HTML
│   │   ├── html_parser.py     # Parsing com BeautifulSoup
│   │   ├── api_client.py      # Cliente API REST Moodle
│   │   └── models.py          # Dataclasses (CourseData, ActivityData, etc.)
│   │
│   ├── detector/
│   │   ├── hasher.py          # SHA-256 do conteúdo normalizado
│   │   ├── comparator.py      # Comparação campo a campo
│   │   └── filter.py          # Filtro de falsos positivos
│   │
│   ├── pipeline/
│   │   ├── pipeline.py        # Orquestrador dos estágios
│   │   └── stages.py          # 6 estágios do pipeline
│   │
│   ├── storage/
│   │   ├── database.py        # Conexão SQLite com WAL
│   │   ├── migrations.py      # Schema e migrações
│   │   └── repository.py      # CRUD para cada tabela
│   │
│   ├── notifier/
│   │   ├── base.py            # Classe abstrata Notifier
│   │   ├── email.py           # Email SMTP
│   │   ├── telegram.py        # Telegram Bot
│   │   └── discord.py         # Discord Webhook
│   │
│   ├── monitor/
│   │   └── engine.py          # Orquestrador principal
│   │
│   ├── scheduler/
│   │   └── scheduler.py       # Agendamento adaptativo com jitter
│   │
│   └── config/
│       └── settings.py        # Leitura de config.yaml + .env
│
└── data/                      # Banco SQLite (criado automaticamente)
    └── monitor.db
```

### 9.6 Fluxo completo (passo a passo)

Quando você roda `python main.py --once`:

1. **main.py** carrega `config.yaml`, resolve `${VARIAVEIS}` do `.env`
2. **MonitorEngine.initialize()**:
   - Cria duas `SessionManager` (portal + moodle)
   - Cria `AuthManager` e chama `authenticate()`
   - AuthManager faz: `validarLogin.php` → `loginAva.php` → login Moodle → token
3. **Pipeline.execute()** roda 6 estágios:
   - **CourseScanStage**: extrai cursos do HTML → filtra pelos `course_ids`
   - **SectionScanStage**: para cada curso, extrai seções e atividades
   - **ActivityDetailStage**: para cada atividade, busca página individual
   - **SnapshotStage**: gera hash e salva estado no SQLite
   - **CompareStage**: compara hash com snapshot anterior → detecta mudanças
   - **NotificationStage**: envia emails (ou Telegram/Discord) com as mudanças
4. **MonitorEngine.shutdown()**: fecha banco, fecha sessions

### 9.7 Casos de erro comuns

| Erro | Causa | Solução |
|------|-------|---------|
| `'sqlite3.Row' object has no attribute 'get'` | Usou `.get()` em resultado de banco | Converter com `dict(row)` antes |
| `cannot commit - no transaction is active` | Operação SQL fora de transação | Verificar se `with db.transaction()` envolve a operação |
| `Link do AVA não encontrado` | `loginAva.php` mudou de formato | Analisar HTML com debug e atualizar parser |
| `SENHA INCORRETA` | RA/senha/campus errados | Verificar no navegador se o login funciona |
| `0 cursos encontrados` | Seletor do dropdown mudou | Verificar HTML do `/my/` e atualizar `_extract_courses_html` |

---

## Glossário

| Termo | Significado |
|-------|-------------|
| **RA** | Registro Acadêmico — número de matrícula (até 10 dígitos) |
| **cmid** | Course Module ID — identificador único de uma atividade no Moodle |
| **sesskey** | Chave de sessão do Moodle (espécie de token CSRF) |
| **MoodleSession** | Cookie de sessão do Moodle |
| **SSO** | Single Sign-On — login único entre sistemas |
| **WAL mode** | Write-Ahead Logging — modo do SQLite que permite leitura durante escrita |
| **SHA-256** | Algoritmo de hash criptográfico (32 bytes) |
| **jitter** | Variação aleatória no intervalo de checagem para evitar padrões |
