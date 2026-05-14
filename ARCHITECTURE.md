# Moodle Monitor — Arquitetura Completa do Sistema

## 1. VISÃO GERAL DA ARQUITETURA

### 1.1 Propósito
Sistema autônomo de monitoramento de portais acadêmicos Moodle que detecta automaticamente novas atividades, alterações em tarefas, mudanças de prazo, novos anexos e conteúdos publicados — independentemente do sistema de notificações nativo do portal.

### 1.2 Princípios Arquiteturais

| Princípio | Descrição |
|-----------|-----------|
| **Resiliência** | Tolerância a falhas de rede, sessão, HTML malformado e API indisponível |
| **Rastreabilidade** | Toda operação é logada com contexto estruturado |
| **Evolutibilidade** | Módulos desacoplados via interfaces; novos extratores, notificadores e comparadores são plugáveis |
| **Determinismo** | Mudanças são detectadas por hash de conteúdo normalizado, não por data de modificação |
| **Eficiência** | Múltiplas disciplinas processadas concorrentemente com backpressure |
| **Segurança** | Credenciais cifradas em repouso, sessão em memória, HTTPS强制 |

### 1.3 Stack Tecnológica

| Camada | Tecnologia | Justificativa |
|--------|-----------|---------------|
| Linguagem | Python 3.14+ | Tipagem opcional, ecossistema rico para scraping (BeautifulSoup, lxml), async nativo (asyncio), ampla adoção |
| HTTP | `httpx` + `requests` | httpx para async, requests para sync com cookie jar maduro |
| HTML | `beautifulsoup4` + `lxml` | Parsing robusto mesmo com HTML malformado; seletores CSS estáveis |
| API | `httpx` + JSON decoder | Consumo das Web Services REST do Moodle |
| Persistência | SQLite via `sqlite3` | Zero dependencies, portátil, transacional, suficiente para single-user |
| Migrações | `sqlite3` schema versioning | Sem framework externo; versão armazenada no próprio banco |
| Hashing | `hashlib` (SHA-256) | Padrão industrial, colisão desprezível |
| Diff | `difflib` (stdlib) | Para gerar diff legível entre descrições HTML |
| Scheduling | `asyncio` loop + heapq | Leve, sem dependency externa; intervalo ajustável por curso |
| Logging | `structlog` + `logging` | Logs estruturados em JSON para análise posterior |
| Notificação | HTTP webhooks + SMTP | Multicanal (Telegram, Discord, Email) via interface polimórfica |
| Config | `PyYAML` + `python-dotenv` | YAML para config estável, .env para secrets |
| Async | `asyncio` + `aiofiles` | Concorrência eficiente sem GIL blocking em I/O |

### 1.4 Visão Geral da Arquitetura (C4 - Nível Container)

```
┌─────────────────────────────────────────────────────────────────┐
│                      Moodle Monitor System                       │
│                                                                   │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐  │
│  │ Scheduler │──▶│ Pipeline │──▶│ Detector │──▶│ Notification  │  │
│  │ (Cron)    │   │ (Stages) │   │ (Engine) │   │ Dispatcher   │  │
│  └──────────┘   └──────────┘   └──────────┘   └──────┬───────┘  │
│       │              │               │                 │         │
│       ▼              ▼               ▼                 ▼         │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐  │
│  │ Auth     │   │ Scraper  │   │ Storage  │   │ Telegram     │  │
│  │ Manager  │   │ Engine   │   │ (SQLite) │   │ Discord      │  │
│  └──────────┘   └──────────┘   └──────────┘   │ Email        │  │
│                                                └──────────────┘  │
│       │              │               │                            │
│       ▼              ▼               ▼                            │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐                      │
│  │ Moodle   │   │ HTML/API │   │ Snapshots│                      │
│  │ Session  │   │ Parsers  │   │ & Logs   │                      │
│  └──────────┘   └──────────┘   └──────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

## 2. ANÁLISE DO PORTAL MOODLE

### 2.1 Endpoints Críticos Identificados

#### 2.1.1 Web Services API do Moodle (Prioridade Máxima)

O Moodle expõe uma API REST completa quando o web service está habilitado. Esta é a fonte **mais confiável e estruturada** de dados.

```
Endpoint base: /webservice/rest/server.php
Formato: REST + JSON
Autenticação: Token via parâmetro wstoken=XXXX
```

**Funções críticas da API:**

| Função | Endpoint | Retorna | Prioridade |
|--------|----------|---------|------------|
| `core_webservice_get_site_info` | Informações do site e token | Site info + user + funções disponíveis | Essencial |
| `core_enrol_get_users_courses` | Cursos do usuário logado | Lista de cursos com IDs | Essencial |
| `core_course_get_contents` | Conteúdo de um curso (seções + módulos + arquivos) | Seções, atividades, recursos, urls | Essencial |
| `core_course_get_courses_by_field` | Cursos por campo (id, shortname, etc.) | Dados do curso | Alta |
| `mod_assign_get_assignments` | Tarefas de um curso | Assignments completos com datas, notas, arquivos | Essencial |
| `mod_assign_get_submission_status` | Status de submissão de uma tarefa | Submissão, notas, feedback, arquivos enviados | Alta |
| `mod_forum_get_forums_by_courses` | Fóruns de um curso | Fóruns com descrições | Média |
| `mod_quiz_get_quizzes_by_courses` | Quizzes de um curso | Quizzes com datas, tempo, notas | Alta |
| `mod_resource_get_resources_by_courses` | Recursos (PDFs, links) | Arquivos e URLs | Alta |
| `core_calendar_get_action_events_by_timesort` | Eventos orders por data | Eventos do calendário com links diretos | Alta |
| `core_completion_get_activities_completion_status` | Status de conclusão | Progresso por atividade | Média |
| `core_course_get_recent_courses` | Cursos acessados recentemente | Cursos com timestamps | Média |

**Estratégia de descoberta do token:**
1. Tentar gerar token via: `POST /login/token.php?username=X&password=Y&service=moodle_mobile_app`
2. Se falhar, extrair token de páginas JS ou HTML
3. Se não existir, usar scraping HTML como fallback

#### 2.1.2 AJAX Internal API (Fallback 1)

O Moodle usa chamadas AJAX internas que retornam JSON:

```
Endpoint: /lib/ajax/service.php?sesskey=XXXX
Método: POST
Headers: Content-Type: application/json
Body: Array de objetos {index, method, args}
```

**Métodos AJAX úteis:**
- `core_course_get_course_module` - info de um módulo específico
- `core_course_get_upcoming_dates` - datas futuras
- `core_calendar_get_calendar_monthly_view` - calendário mensal
- `core_course_get_navigation` - navegação do curso

#### 2.1.3 HTML Scraping (Fallback 2)

**Páginas principais para scraping:**

```
/course/view.php?id={course_id}
    → Lista de seções com atividades (nome, tipo, link, datas)
    → Breadcrumbs para contexto
    → Cada atividade dentro de um <li> com classes CSS específicas

/mod/assign/view.php?id={cmid}
    → Página individual da tarefa
    → Descrição completa
    → Datas (abertura, fechamento, entrega)
    → Arquivos anexados
    → Notas máximas

/mod/resource/view.php?id={cmid}
    → Recurso (PDF, link)
    → Arquivo para download

/mod/quiz/view.php?id={cmid}
    → Quiz com datas e duração

/mod/forum/view.php?id={cmid}
    → Fórum com discussões

/user/index.php?id={course_id}
    → Participantes do curso

/grade/report/user/index.php?id={course_id}
    → Notas do usuário no curso
```

**Seletores CSS identificados (estáveis no Moodle 3.x-4.x):**

```css
/* Lista de atividades no curso */
li.activity { ... }
span.instancename { ... }
div.contentafterlink { ... }
div.activityinstance { ... }

/* Datas */
div.dates { ... }
div.assignment-dates { ... }

/* Arquivos */
div.fileuploadsubmission { ... }
a[href*="pluginfile.php"] { ... }

/* Descrições */
div.no-overflow { ... }
div.description { ... }

/* Breadcrumbs */
nav.breadcrumb { ... }
span.breadcrumb-item { ... }

/* Navegação */
section.course-content { ... }
ul.topics li.section { ... }
li.section .content { ... }
h3.sectionname { ... }
```

### 2.2 Fluxo Real de Autenticação (Dois Portais)

O portal alvo (UNISALESIANO) utiliza um fluxo de **dois domínios**:

```
1. Portal Institucional (customizado)
   URL: https://unisalesiano.com.br/salaEstudo/alunos/
   ├── Formulário: POST /salaEstudo/alunos/validarLogin.php
   ├── Campos: idCasa (unidade), ra, senha
   ├── idCasa=12 → UNISALESIANO Lins
   ├── idCasa=13 → UNISALESIANO Araçatuba
   └── Sucesso → redirect para /salaEstudo/alunos/menu.php

2. Menu Intermediário
   URL: https://unisalesiano.com.br/salaEstudo/alunos/menu.php
   ├── Contém link para o AVA (Ambiente Virtual de Aprendizagem)
   └── Link aponta para missaosalesiana.mrooms.net

3. Moodle (Open LMS)
   URL: https://missaosalesiana.mrooms.net/
   ├── Tema: Snap (customizado)
   ├── Login: /login/index.php (padrão Moodle)
   ├── API: /webservice/rest/server.php
   ├── Token: /login/token.php
   └── Sessão: cookie MoodleSession
```

**Estratégia de autenticação implementada:**

```
AuthManager.authenticate():
  1. _login_portal()
     → POST validarLogin.php com RA + senha + unidade
     → Sessão estabelecida em unisalesiano.com.br

  2. _extract_ava_link()
     → GET menu.php (com cookie do portal)
     → Extrai link do AVA via BeautifulSoup + regex
     → Padrões: "missaosalesiana.mrooms.net" ou texto "AVA"/"Moodle"

  3. _login_moodle()
     → 3 tentativas em cascata:
        a. _try_sso_via_ava() — segue o link do AVA, copia cookies do portal
        b. _try_direct_moodle_login() — login direto em /login/index.php
        c. _try_moodle_token_auth() — token via /login/token.php
```

**Duas sessões independentes:**
- `portal_session` (unisalesiano.com.br) — apenas para login inicial
- `moodle_session` (missaosalesiana.mrooms.net) — para todo scraping e API

### 2.3 Análise de Sessão e Autenticação

O Moodle usa autenticação baseada em sessão:

```
Fluxo de login:
1. GET /login/index.php → obtém token de logintoken (CSRF)
2. POST /login/index.php → envia username, password, logintoken
3. Resposta define cookie MoodleSession={hash}
4. Todas as requisições subsequentes usam o cookie
```

**Cookie necessário:** `MoodleSession` — valor críptico, validade configurável (tipicamente 8h-48h)

**Estratégia de renovação:**
- Antes de expirar (detectado por redirect para /login/ no body da resposta), re-autenticar automaticamente
- Se detectar "redirect" para login, limpar sessão e re-autenticar
- Manter sessão em memória (nunca em disco)

## 3. ARQUITETURA EM CAMADAS

### 3.1 Diagrama de Camadas

```
┌────────────────────────────────────────────────────────────────────┐
│                        APPLICATION LAYER                           │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────────────┐  │
│  │ Scheduler   │  │ Pipeline    │  │ Monitor Engine            │  │
│  │ (quando     │──│ (o quê)     │──│ (como, coordinator)       │  │
│  │  executar)  │  │             │  │                           │  │
│  └─────────────┘  └─────────────┘  └───────────┬───────────────┘  │
├──────────────────────────────────────────────────┼─────────────────┤
│                   DOMAIN LAYER                   │                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────▼───────────┐   │
│  │ Auth Service │  │ Scraper      │  │ Detector             │   │
│  │ (quem é)     │  │ (onde buscar)│  │ (o que mudou)        │   │
│  └──────────────┘  └──────────────┘  └──────────┬───────────┘   │
│                                                   │              │
│  ┌───────────────────────────────────────────────▼────────┐     │
│  │ Storage Service (como persistir)                       │     │
│  └────────────────────────────────────────────────────────┘     │
├──────────────────────────────────────────────────────────────────┤
│                    INFRASTRUCTURE LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ HTTP Client  │  │ SQLite       │  │ Notification Senders  │  │
│  │ (httpx)      │  │ (sqlite3)    │  │ (Telegram/Discord)   │  │
│  └──────────────┘  └──────────────┘  └───────────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│                    EXTERNAL SYSTEMS                               │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Moodle       │  │ SQLite File  │  │ Telegram API          │  │
│  │ Portal       │  │ (.db)        │  │ Discord Webhook       │  │
│  └──────────────┘  └──────────────┘  └───────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Fluxo de Dados Detalhado

```
INÍCIO (main.py)
    │
    ▼
[1. Carregar Configuração]
    ├── config.yaml (estrutura)
    └── .env (credenciais + tokens)
    │
    ▼
[2. Inicializar Storage]
    ├── Conectar SQLite
    ├── Executar migrações
    └── Verificar integridade
    │
    ▼
[3. Autenticar no Moodle]
    ├── Tentar token API (webservice)
    │   ├── Sucesso → Modo API + HTML
    │   └── Falha → Modo somente HTML
    ├── Login via formulário
    └── Validar sessão
    │
    ▼
[4. Iniciar Scheduler (loop principal)]
    │
    ├─► [A CADA 15 MINUTOS] ────────────────────────────────┐
    │                                                        │
    ▼                                                        │
[5. Executar Pipeline de Monitoramento]                      │
    │                                                        │
    ├── 5.1. Course Scanner                                  │
    │       ├── Listar cursos do usuário                     │
    │       │   ├── API: core_enrol_get_users_courses        │
    │       │   └── Fallback: HTML /course/                  │
    │       └── Para cada curso (paralelo, max 5):           │
    │                                                        │
    ├── 5.2. Section Scanner                                 │
    │       ├── API: core_course_get_contents                │
    │       └── Fallback: HTML /course/view.php?id=X         │
    │                                                        │
    ├── 5.3. Activity Scanner                                │
    │       ├── Extrair módulos (assign, quiz, resource...)  │
    │       ├── API específica por tipo                     │
    │       └── Fallback: HTML específico por tipo           │
    │                                                        │
    ├── 5.4. Data Normalizer                                 │
    │       ├── Converter HTML → texto normalizado           │
    │       ├── Extrair arquivos → lista de hashes           │
    │       └── Normalizar datas → ISO 8601                  │
    │                                                        │
    ├── 5.5. Snapshot Generator                              │
    │       ├── Calcular hash SHA-256 do estado              │
    │       └── Armazenar snapshot atual                     │
    │                                                        │
    ├── 5.6. Change Comparator                               │
    │       ├── Comparar hash atual vs último hash           │
    │       ├── Se diferente → identificar campo mudado      │
    │       └── Gerar diff estruturado                       │
    │                                                        │
    ├── 5.7. Notification Builder                            │
    │       ├── Classificar mudança (tipo, severidade)       │
    │       └── Montar mensagem formatada                    │
    │                                                        │
    └── 5.8. Notification Dispatcher                         │
            ├── Enviar para todos os canais configurados     │
            ├── Registrar na tabela de notificações          │
            └── Retentar em caso de falha (max 3)            │
                                                            │
    ◄────────────────────────────────────────────────────────┘
    │
    ▼
[6. Dormir até próximo ciclo]
```

## 4. MODELO DE DADOS

### 4.1 Diagrama Entidade-Relacionamento

```
┌──────────────┐       ┌──────────────────┐
│    User      │       │   Course          │
│──────────────│       │──────────────────│
│ id (PK)      │       │ id (PK)          │
│ username     │1───▶N│ moodle_course_id  │
│ portal_url   │       │ fullname         │
│ is_active    │       │ shortname        │
│ created_at   │       │ summary          │
│ updated_at   │       │ category         │
└──────────────┘       │ is_active         │
                       │ last_check_at     │
                       │ created_at        │
                       └────────┬─────────┘
                                │
                                │ 1
                                │
                       ┌────────▼─────────┐
                       │   Section         │
                       │──────────────────│
                       │ id (PK)           │
                       │ course_id (FK)    │N──────┐
                       │ moodle_section_id │       │
                       │ name              │       │
                       │ position          │       │
                       └───────────────────┘       │
                                                   │ 1
                       ┌──────────────────────────┐│
                       │       Activity            ││
                       │──────────────────────────┘│
                       │ id (PK)                   │
                       │ course_id (FK)            │
                       │ section_id (FK)           │
                       │ moodle_cmid               │
                       │ activity_type             │
                       │ moodle_instance_id        │
                       │ name                      │
                       │ url                       │
                       │ is_active                 │
                       │ first_seen_at             │
                       │ last_checked_at           │
                       └────────────┬──────────────┘
                                    │ 1
                                    │
                      ┌─────────────▼──────────────┐
                      │     ActivitySnapshot        │
                      │────────────────────────────│
                      │ id (PK)                    │
                      │ activity_id (FK)           │
                      │ version                    │
                      │ name                       │
                      │ description                │
                      │ description_hash           │
                      │ due_date                   │
                      │ open_date                  │
                      │ cutoff_date                │
                      │ max_grade                  │
                      │ files_hash                 │
                      │ full_hash                  │
                      │ taken_at                   │
                      └────────────┬──────────────┘
                                   │ 1
                                   │
                      ┌────────────▼──────────────┐
                      │     ActivityFile           │
                      │───────────────────────────│
                      │ id (PK)                   │
                      │ activity_id (FK)          │
                      │ snapshot_id (FK)          │
                      │ filename                  │
                      │ file_url                  │
                      │ file_size                 │
                      │ file_hash (SHA-256)       │
                      │ mimetype                  │
                      │ discovered_at             │
                      └────────────┬──────────────┘
                                   │
                      ┌────────────▼──────────────┐
                      │     DetectedChange         │
                      │───────────────────────────│
                      │ id (PK)                   │
                      │ activity_id (FK)          │
                      │ change_type               │
                      │ old_value                 │
                      │ new_value                 │
                      │ diff                      │
                      │ snapshot_from_id (FK)     │
                      │ snapshot_to_id (FK)       │
                      │ severity                  │
                      │ notified                  │
                      │ detected_at               │
                      └────────────┬──────────────┘
                                   │
                      ┌────────────▼──────────────┐
                      │     NotificationLog        │
                      │───────────────────────────│
                      │ id (PK)                   │
                      │ change_id (FK)            │
                      │ channel                   │
                      │ delivered                 │
                      │ error                     │
                      │ sent_at                   │
                      └───────────────────────────┘
```

### 4.2 Estrutura das Entidades (Python)

```python
@dataclass
class Course:
    id: str
    moodle_course_id: int
    fullname: str
    shortname: str
    summary: str | None
    category: str | None
    is_active: bool
    last_check_at: datetime | None
    created_at: datetime
    updated_at: datetime

@dataclass
class Activity:
    id: str
    course_id: str
    section_id: str | None
    moodle_cmid: int
    activity_type: str  # assign, quiz, forum, resource, page, url, etc.
    moodle_instance_id: int
    name: str
    description: str | None
    url: str
    is_active: bool
    first_seen_at: datetime
    last_checked_at: datetime

@dataclass
class ActivitySnapshot:
    id: str
    activity_id: str
    version: int
    name: str
    description: str | None
    description_hash: str | None
    due_date: datetime | None
    open_date: datetime | None
    cutoff_date: datetime | None
    max_grade: float | None
    files_hash: str | None
    full_hash: str
    taken_at: datetime

@dataclass
class ActivityFile:
    id: str
    activity_id: str
    snapshot_id: str | None
    filename: str
    file_url: str
    file_size: int | None
    file_hash: str | None
    mimetype: str | None
    discovered_at: datetime

@dataclass
class DetectedChange:
    id: str
    activity_id: str
    change_type: ChangeType  # Enum
    old_value: str | None
    new_value: str | None
    diff: str | None
    snapshot_from_id: str | None
    snapshot_to_id: str
    severity: Severity  # Enum
    notified: bool
    detected_at: datetime

@dataclass
class ChangeType(StrEnum):
    NEW_ACTIVITY = "new_activity"
    DESCRIPTION_CHANGE = "description_change"
    DEADLINE_CHANGE = "deadline_change"
    FILE_ADDED = "file_added"
    FILE_REMOVED = "file_removed"
    GRADE_CHANGE = "grade_change"
    NAME_CHANGE = "name_change"
    AVAILABILITY_CHANGE = "availability_change"
    SECTION_CHANGE = "section_change"
```

## 5. ESTRATÉGIA DE DETECÇÃO DE MUDANÇAS

### 5.1 Algoritmo de Hashing

```
Para cada atividade, computar FULL_HASH como:

FULL_HASH = SHA-256(
    normalized(name) + "|" +
    normalized(description) + "|" +
    datestring(due_date) + "|" +
    datestring(open_date) + "|" +
    datestring(cutoff_date) + "|" +
    str(max_grade) + "|" +
    FILES_HASH
)

FILES_HASH = SHA-256(
    sorted(
        SHA-256(filename + file_size + file_url)
        for each file
    ).join("|")
)
```

### 5.2 Matriz de Detecção

| Mudança | Campo alterado | Como detectar | Severidade |
|---------|---------------|---------------|------------|
| Nova atividade | N/A | Atividade existe no portal mas não no banco | critical |
| Descrição alterada | description_hash ≠ | comparação de hash | warning |
| Prazo alterado | due_date ≠ | comparação de data | critical |
| Novo arquivo | files_hash ≠; file novo | diff na lista de arquivos | warning |
| Arquivo removido | file sumiu do files_hash | diff na lista de arquivos | info |
| Nome alterado | name ≠ | comparação direta | warning |
| Nota máxima alterada | max_grade ≠ | comparação direta | info |
| Data de abertura alterada | open_date ≠ | comparação direta | info |

### 5.3 Prevenção de Falsos Positivos

1. **Normalização de HTML** antes de hashing:
   - Remover tags de estilo, script, meta
   - Remover atributos dinâmicos (data-*, on*, style)
   - Remover whitespace extra
   - Remover "Adicionado: ..." timestamps dinâmicos

2. **Ignorar campos voláteis**:
   - Contadores de visualização
   - "Última modificação" do sistema
   - Elementos de interação (botões, formulários)

3. **Cooldown de notificações**:
   - Mesmo tipo de mudança para mesma atividade só notifica uma vez a cada 30 min
   - Se múltiplas mudanças em curto período, agrupar em única notificação

4. **Threshold de diff**:
   - Mudanças < 3 caracteres no texto são ignoradas
   - Whitespace-only changes são ignoradas

## 6. ESTRATÉGIA DE CONCORRÊNCIA

### 6.1 Modelo de Concorrência

```
                    ┌──────────────────┐
                    │   Main Loop      │
                    │   (asyncio)      │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   Scheduler      │
                    │  (intervalos)    │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ Pipeline Runner  │
                    │  (asyncio)       │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼────┐ ┌──────▼──────┐ ┌─────▼──────┐
     │ Course 1    │ │ Course 2    │ │ Course N   │
     │ (Task)      │ │ (Task)      │ │ (Task)     │
     └────────┬────┘ └──────┬──────┘ └─────┬──────┘
              │             │              │
     ┌────────▼────┐ ┌──────▼──────┐ ┌─────▼──────┐
     │ Activity 1  │ │ Activity M  │ │ Activity K │
     │ (Task)      │ │ (Task)      │ │ (Task)     │
     └────────┬────┘ └──────┬──────┘ └─────┬──────┘
              │             │              │
              └──────┬──────┴──────┬───────┘
                     │             │
              ┌──────▼──────┐ ┌────▼────────┐
              │ Comparator  │ │ Storage     │
              │ (sequential)│ │ (sequential)│
              └──────┬──────┘ └──────┬──────┘
                     │               │
              ┌──────▼───────────────▼──────┐
              │   Notification Dispatcher   │
              │   (async, fan-out)          │
              └─────────────────────────────┘
```

### 6.2 Parâmetros de Concorrência

| Parâmetro | Valor | Motivo |
|-----------|-------|--------|
| Max courses simultâneos | 5 | Evitar sobrecarga no portal |
| Max activities por curso | 10 | Limite por worker |
| Intervalo normal | 15 min | Detecção rápida sem excesso de requests |
| Intervalo prazo < 24h | 5 min | Atividades urgentes têm prioridade |
| Intervalo prazo expirado | 60 min | Reduz polling desnecessário |
| Backoff após erro N consecutivos | *2 (30s→1m→2m→...→max 1h) | Evitar flood |
| Timeout request | 30s | Não travar em página lenta |
| Jitter | ±20% do intervalo | Evitar padrão previsível |
| Max retries por request | 3 | Tentar novamente antes de falhar |

## 7. ESTRATÉGIA DE ARMAZENAMENTO

### 7.1 SQLite Schema

O banco SQLite contém 9 tabelas principais mais índices otimizados.

**Índices estratégicos:**
```sql
-- Busca rápida de atividades por curso
CREATE INDEX idx_activities_course ON activities(course_id, is_active);

-- Busca de último snapshot de cada atividade
CREATE INDEX idx_snapshots_activity_version ON activity_snapshots(activity_id, version DESC);

-- Busca de mudanças não notificadas
CREATE INDEX idx_changes_notified ON detected_changes(notified, detected_at);

-- Busca de notificações por mudança
CREATE INDEX idx_notification_log_change ON notification_log(change_id);

-- Busca temporal
CREATE INDEX idx_snapshots_taken_at ON activity_snapshots(taken_at);
CREATE INDEX idx_changes_detected_at ON detected_changes(detected_at);
```

### 7.2 Política de Retenção

| Dado | Retenção | Motivo |
|------|----------|--------|
| Snapshots de atividades | 90 dias | Histórico para comparação |
| Mudanças detectadas | 180 dias | Auditoria e debugging |
| Logs de notificação | 90 dias | Rastreabilidade |
| Atividades inativas | Indefinido (marcadas is_active=false) | Não perder histórico |
| Logs de erro | 30 dias | Diagnóstico |

## 8. ESTRATÉGIA DE NOTIFICAÇÕES

### 8.1 Arquitetura de Notificações

```python
# Interface (Protocol) para todos os notificadores:
class Notifier(Protocol):
    async def send(self, change: DetectedChange, activity: Activity, course: Course) -> bool: ...
    async def health_check(self) -> bool: ...
```

**Implementações atuais:**
- `TelegramNotifier` — Bot do Telegram via API HTTP
- `DiscordNotifier` — Webhook do Discord
- `EmailNotifier` — SMTP com template HTML

### 8.2 Templates de Notificação

**Template base (Markdown universal):**
```
┌─────────────────────────────────────────┐
│  {emoji} {change_type_human}             │
│                                          │
│  📚 Disciplina: {course_fullname}       │
│  📝 Atividade: {activity_name}          │
│  🔗 Link: {activity_url}               │
│                                          │
│  {details}                               │
│                                          │
│  🕐 Detectado em: {detected_at}         │
└─────────────────────────────────────────┘
```

**Exemplo por tipo:**

📝 *Nova atividade detectada!*
📚 Disciplina: Análise e Projeto de Sistemas
📝 Atividade: Trabalho Final - Documentação
📎 Tipo: Tarefa (Assign)
📅 Data de entrega: 20/05/2026 23:59
🔗 Link: https://portal.exemplo.br/mod/assign/view.php?id=12345

⚠️ *Prazo alterado!*
📚 Disciplina: Engenharia de Software III
📝 Atividade: Projeto Prático - Sprint 2
📅 Prazo anterior: 15/05/2026 23:59
📅 Novo prazo: 22/05/2026 23:59
🔗 Link: https://portal.exemplo.br/mod/assign/view.php?id=12346

📎 *Novo arquivo disponível!*
📚 Disciplina: Banco de Dados II
📝 Atividade: Modelagem Conceitual
📄 Arquivo: modelo_conceitual_exemplo.pdf (2.4 MB)
🔗 Link: https://portal.exemplo.br/mod/resource/view.php?id=12347

### 8.3 Política de Notificação

| Tipo de mudança | Notificar? | Canal preferido |
|----------------|------------|----------------|
| Nova atividade | Sim, imediatamente | Todos |
| Prazo alterado | Sim, imediatamente | Todos (warning) |
| Descrição alterada | Sim, imediatamente | Todos |
| Novo arquivo | Sim, imediatamente | Todos |
| Arquivo removido | Não (info only) | Log |
| Nome alterado | Sim (se título mudar muito) | Todos |
| Nota alterada | Sim | Todos |

## 9. ESTRATÉGIA DE LOGS

### 9.1 Estrutura de Log

```json
{
    "timestamp": "2026-05-14T10:30:00.123456Z",
    "level": "info",
    "logger": "moodle_monitor.scraper.course",
    "message": "Course scanned successfully",
    "context": {
        "course_id": 42,
        "course_name": "Análise de Sistemas",
        "sections_found": 8,
        "activities_found": 15,
        "duration_ms": 1234,
        "source": "api"
    },
    "trace_id": "abc123def456"
}
```

### 9.2 Níveis de Log

| Nível | Uso |
|-------|-----|
| DEBUG | HTML baixado, requests individuais, hashes computados |
| INFO | Operações bem-sucedidas, atividades encontradas, mudanças detectadas |
| WARNING | Timeout, retry, sessão renovada, HTML malformado |
| ERROR | Falha de autenticação, erro de rede, banco corrompido |
| CRITICAL | Credenciais inválidas, banco inacessível, erro irrecuperável |

### 9.3 Canais de Log

- **Console**: stdout com cores (desenvolvimento)
- **Arquivo rotacionado**: `logs/monitor.{date}.json` (produção)
- **Banco SQLite**: tabela `error_log` para consulta via app (futuro)

## 10. ESTRATÉGIA DE RECUPERAÇÃO DE FALHAS

### 10.1 Matriz de Falhas e Recuperação

| Falha | Detecção | Ação | Recuperação |
|-------|----------|------|-------------|
| Sessão expirada | Redirect p/ login ou body contém "login" | Re-autenticar imediatamente | Continuar ciclo atual |
| Token API inválido | HTTP 403 no webservice | Renovar token ou fallback HTML | Tentar novamente no próximo ciclo |
| Timeout de rede | httpx.TimeoutException | Retry com backoff exponencial | Marcar course como "degradado" |
| HTML malformado | BeautifulSoup não encontra elementos | Log WARNING, fallback para API | Tentar HTML novamente no próximo ciclo |
| Erro 5xx do portal | HTTP 500/502/503 | Retry 3x com backoff, depois pular ciclo | Tentar no próximo ciclo normal |
| Erro de conexão DNS | socket.gaierror | Retry 3x, depois ERROR | Marcar portal como offline |
| SQLite locked | sqlite3.OperationalError | Retry 3x com 1s de intervalo | Continuar |
| Disco cheio | IOError no storage | ERROR crítico, notificar admin | Parar operação |
| Credenciais inválidas | Login retorna erro | CRITICAL, notificar admin | Parar operação até intervenção |

### 10.2 Estado Persistente para Recovery

```sql
CREATE TABLE monitor_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Keys:
-- session_valid: true/false
-- consecutive_errors: int
-- last_successful_check: ISO timestamp
-- last_check_duration_ms: int
-- current_version: string (git commit/version)
```

## 11. ESTRATÉGIA DE SEGURANÇA

### 11.1 Proteção de Credenciais

```
Credenciais:
    - Nunca armazenadas em disco como texto plano
    - Armazenadas cifradas com AES-256-GCM
    - Chave de cifra derivada de senha mestra via PBKDF2 (100k iterações)
    - Ou fornecidas via .env file (não versionado)

Sessão:
    - Cookies armazenados apenas em memória
    - Session key (sesskey) extraída de cada página
    - Jamais logada
    - Duas sessões independentes (portal + moodle)

Transporte:
    - HTTPS verificado (certificate validation)
    - User-Agent customizado (não o padrão do Python)
    - Rate limiting: max 2 requests/segundo por portal
```

### 11.2 Arquivo .env Example

```
# Portal Institucional (login customizado)
PORTAL_URL=https://unisalesiano.com.br/salaEstudo/alunos/
PORTAL_USERNAME=seu_ra
PORTAL_PASSWORD=sua_senha
PORTAL_CAMPUS_ID=12

# Moodle (AVA)
MOODLE_URL=https://missaosalesiana.mrooms.net/

# Tokens de Notificação
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl...
TELEGRAM_CHAT_ID=123456789
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=seu_email@gmail.com
SMTP_PASSWORD=sua_senha_app
NOTIFICATION_EMAIL=seu_email@gmail.com

# Opcionais
LOG_LEVEL=INFO
CHECK_INTERVAL_MINUTES=15
DATA_DIR=./data
```

## 12. ESTRATÉGIA DE ESCALABILIDADE

### 12.1 Single User → Multi User (Futuro)

| Aspecto | Single User (MVP) | Multi User (SaaS) |
|---------|-------------------|-------------------|
| Database | SQLite | PostgreSQL |
| Concorrência | asyncio tasks | Worker pool + message queue |
| Auth | .env credentials | Per-user encrypted credentials |
| Scheduler | In-process heapq | Redis + Celery / APScheduler |
| Web UI | CLI only | FastAPI + React |
| Notifications | Telegram/Discord | Same + WebSocket/Push |
| Storage | Local file | S3/GCS for files |

### 12.2 Preparação para SaaS

- Repository pattern já abstrai o banco de dados
- Notifier interface permite adicionar canais sem modificar core
- Pipeline de processamento é stateless por curso
- Detector opera em memória com estado do banco
- Config é injetada via dependency injection

## 13. ESTRUTURA DE PASTAS

```
moodle-monitor/
├── ARCHITECTURE.md              ← Este documento
├── config.yaml                  ← Configuração do monitor
├── .env.example                 ← Template de variáveis de ambiente
├── requirements.txt             ← Dependências Python
├── pyproject.toml               ← Metadados do projeto
├── setup.cfg                    ← Config de ferramentas
├── main.py                      ← Entry point principal
│
├── src/
│   ├── __init__.py
│   │
│   ├── auth/                    ← Autenticação e sessão Moodle
│   │   ├── __init__.py
│   │   ├── session.py           ← Gerenciador de sessão HTTP
│   │   └── moodle_auth.py       ← Estratégias de autenticação
│   │
│   ├── scraper/                 ← Extração de dados do portal
│   │   ├── __init__.py
│   │   ├── api_client.py        ← Cliente da Web Services API
│   │   ├── html_parser.py       ← Parser de HTML (BeautifulSoup)
│   │   ├── extractor.py         ← Estratégias de extração por tipo
│   │   └── models.py            ← Modelos de dados do Moodle
│   │
│   ├── detector/                ← Detecção de mudanças
│   │   ├── __init__.py
│   │   ├── hasher.py            ← Sistema de hashing de conteúdo
│   │   ├── comparator.py        ← Comparador de snapshots
│   │   └── filter.py            ← Filtro de falsos positivos
│   │
│   ├── storage/                 ← Persistência
│   │   ├── __init__.py
│   │   ├── database.py          ← Conexão e operações SQLite
│   │   ├── repository.py        ← Repositórios (CRUD)
│   │   └── migrations.py        ← Migrações de schema
│   │
│   ├── notifier/                ← Notificações multicanal
│   │   ├── __init__.py
│   │   ├── base.py              ← Interface do notificador
│   │   ├── telegram.py          ← Notificador Telegram
│   │   ├── discord.py           ← Notificador Discord
│   │   └── email.py             ← Notificador Email
│   │
│   ├── scheduler/               ← Agendamento de tarefas
│   │   ├── __init__.py
│   │   └── scheduler.py         ← Scheduler assíncrono
│   │
│   ├── pipeline/                ← Pipeline de processamento
│   │   ├── __init__.py
│   │   ├── pipeline.py          ← Orquestrador do pipeline
│   │   └── stages.py            ← Estágios do pipeline
│   │
│   ├── monitor/                 ← Motor de monitoramento
│   │   ├── __init__.py
│   │   └── engine.py            ← Engine principal
│   │
│   └── config/                  ← Configuração
│       ├── __init__.py
│       └── settings.py          ← Carregamento de config
│
├── tests/                       ← Testes (futuro)
│   ├── test_auth.py
│   ├── test_scraper.py
│   ├── test_detector.py
│   └── test_pipeline.py
│
├── logs/                        ← Logs rotacionados
│   └── .gitkeep
│
└── data/                        ← Dados persistidos
    └── .gitkeep
```

## 14. FLUXOGRAMA COMPLETO

```
                    ┌─────────────────────────┐
                    │     INÍCIO              │
                    │  main.py                │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Carregar Config        │
                    │  config.yaml + .env     │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Inicializar Logger     │
                    │  structlog config       │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Inicializar Storage    │
                    │  SQLite + Migrações     │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Autenticar no Moodle ──┼──▶ Sessão OK?
                    │  AuthManager.login()    │       │
                    └───────────┬─────────────┘       │
                                │ Sim                 │ Não
                                ▼                     ▼
                    ┌─────────────────────┐  ┌──────────────┐
                    │  Iniciar Scheduler  │  │ Log CRITICAL │
                    │  Loop Principal     │  │ Abortar      │
                    └───────────┬─────────┘  └──────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Aguardar intervalo     │
                    │  (sleep ajustado)       │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Pipeline.executar()    │
                    └───────────┬─────────────┘
                                │
              ┌─────────────────┼──────────────────┐
              │                                     │
    ┌─────────▼─────────┐               ┌──────────▼──────────┐
    │  Sessão válida?    │               │  Pipeline Steps     │
    │  Verificar cookie  │               │                     │
    └─────────┬─────────┘               │  1. Listar cursos   │
              │                         │  2. Listar seções   │
              ├── Não → Re-autenticar   │  3. Listar ativ.    │
              │                         │  4. Extrair dados   │
              │ Sim                     │  5. Normalizar      │
              │                         │  6. Hashear         │
              ▼                         │  7. Comparar        │
    ┌──────────────────────┐            │  8. Detectar mud.   │
    │  Executar Pipeline   │            │  9. Notificar       │
    └──────────────────────┘            │  10. Persistir      │
              │                         └─────────────────────┘
              │
              ▼
    ┌──────────────────────┐
    │  Registrar estado    │
    │  Atualizar timestamps│
    └──────────────────────┘
              │
              ▼
    ┌──────────────────────┐
    │  Log conclusão       │
    │  + métricas          │
    └──────────────────────┘
              │
              ▼
    ┌──────────────────────┐
    │  Loop (volta p/      │
    │  aguardar intervalo) │
    └──────────────────────┘
```

## 15. DECISÕES ARQUITETURAIS (ADRs)

### ADR-001: API primeiro, HTML como fallback
**Contexto:** Moodle expõe Web Services REST que retornam dados estruturados.
**Decisão:** Sempre tentar a API primeiro. Fallback para HTML apenas se API falhar.
**Consequências:** Mais confiável (dados estruturados), menos propenso a quebras por mudanças de template HTML.

### ADR-002: SQLite como storage primário
**Contexto:** Sistema single-user, sem necessidade de concorrência de escritas.
**Decisão:** SQLite é suficiente, zero config, portátil, transacional.
**Consequências:** Simplicidade de deploy, sem dependência externa, fácil backup (copia arquivo .db).
**Futuro:** Repository pattern permite trocar para PostgreSQL com mínimo impacto.

### ADR-003: Hashing baseado em conteúdo, não em data
**Contexto:** Datas de modificação podem ser alteradas pelo sistema sem mudança real de conteúdo.
**Decisão:** Usar SHA-256 do conteúdo normalizado para detectar mudanças.
**Consequências:** Zero falsos positivos por metadados, 100% determinístico.

### ADR-004: Intervalo de polling adaptativo
**Contexto:** Diferentes atividades têm diferentes níveis de urgência.
**Decisão:** Frequência baseada em proximidade do prazo e histórico de mudanças.
**Consequências:** Menos carga no portal, notificações mais rápidas para atividades urgentes.

### ADR-005: Concorrência via asyncio
**Contexto:** I/O-bound operation (HTTP requests, database, file I/O).
**Decisão:** asyncio com semáforos para controle de concorrência.
**Consequências:** Eficiente para I/O, sem overhead de threads, backpressure natural.

## 16. MÉTRICAS E MONITORAMENTO (DO SISTEMA)

### 16.1 Métricas Coletadas

```
# Runtime
monitor.uptime_seconds
monitor.courses_active
monitor.activities_tracked
monitor.snapshots_stored
monitor.changes_detected_total{type="..."}

# Performance
monitor.check_duration_ms{course_id="..."}
monitor.api_latency_ms{endpoint="..."}
monitor.html_parse_ms{course_id="..."}
monitor.hash_compute_ms

# Reliability
monitor.auth_failures_total
monitor.api_failures_total{endpoint="..."}
monitor.html_parse_failures_total
monitor.session_renewals_total
monitor.consecutive_errors{course_id="..."}

# Notifications
monitor.notifications_sent_total{channel="..."}
monitor.notification_failures_total{channel="..."}
monitor.notification_latency_ms{channel="..."}
```

### 16.2 Health Check Endpoint (Futuro Web UI)

```
GET /health → {
    "status": "healthy" | "degraded" | "down",
    "uptime": 3600,
    "last_check_ago": 30,
    "session_valid": true,
    "courses_ok": 5,
    "courses_failing": 0,
    "active_activities": 42,
    "pending_changes": 3,
    "storage_size_mb": 12.5
}
```

---

*Arquitetura v1.0 — Projetada para ser um produto real, não um script descartável.*
