# Contexto da Conversa — 14/05/2026

## Problema
Frontend React (Vite) estava mostrando **white screen** devido à falta de proxy do Vite para o backend FastAPI. API calls (axios) estavam indo para `http://localhost:5173/api/...` em vez de `http://localhost:8000/api/...`.

## O que foi feito

### 1. White screen resolvido
- Adicionado proxy em `frontend/vite.config.ts`: `/api` → `http://127.0.0.1:8000`
- Todas as chamadas axios com `baseURL: '/api'` agora funcionam tanto em dev (proxy Vite) quanto em produção (mesmo domínio).

### 2. Backend FastAPI — correções e novos endpoints

**Sync filter por disciplina:**
- `sync_service.sync()` agora aceita `course_ids: list[int] | None`
- Quando passado, a query SQL filtra por `c.moodle_course_id IN (...)` — só as 11 disciplinas do `config.yaml`
- Lido de `config.yaml` no router `POST /api/sync`

**publication_date populado no sync:**
- O sync agora copia `a.first_seen_at` da `monitor.db` para `tasks.publication_date` no `study.db`
- Todas as 154 tasks têm `publication_date` preenchido (entre 14-15/05/2026)

**Filtro por data de vencimento:**
- `GET /api/activities/vigent` aceita `due_date_before` e `due_date_after` (ISO date strings)
- `due_date_after` inclui tasks com `due_date IS NULL` (atividades sem prazo são consideradas vigentes)

### 3. Frontend — Atividades Vigentes

**Filtro automático por data:**
- `ActivityList` passa `due_date_after=today` (YYYY-MM-DD) na chamada `fetchVigentActivities`
- Só aparecem atividades com vencimento a partir de hoje (ou sem data de vencimento)

**Display de data fallback:**
- Card mostra `due_date` quando existe; senão mostra `"Pub. DD/MM"` com `publication_date`

### 4. Banco de dados
- `study.db` limpo e reimportado com filtro de curso: **520 → 154 tasks**
- Todas as 154 pertencem às 11 disciplinas do `config.yaml`
- Nenhuma task tem `due_date` — o scraper não capturou prazos (1650 snapshots sem `due_date`)

## Sobre o scraper original
O scraper em `src/scraper/` extrai dados do Moodle via API REST (token) ou HTML fallback (BeautifulSoup). Campos extraíveis por atividade:

| Campo | Fonte |
|-------|-------|
| `cmid`, `instance_id` | ID Moodle |
| `type` | assign, quiz, forum, resource... |
| `name` | Título |
| `url` | Link direto |
| `description` | Descrição em texto |
| `due_date` | Prazo final (API: `duedate`/`timeclose`; HTML: texto "Data de entrega") |
| `open_date` | Data de abertura |
| `cutoff_date` | Data limite (assignments) |
| `max_grade` | Nota máxima |
| `files` | Arquivos anexados |
| `section_id/name` | Tópico/seção |

**Problema:** O scraper salvou 1650 snapshots sem `due_date`. Possível causa: está rodando via HTML sem token API, e a página de listagem do curso não exibe prazos.

## Pendências / Ideias
- Configurar **token Moodle** no `.env` para API REST capturar `due_date` e `max_grade`
- Ou modificar o scraper para acessar **página individual** de cada atividade (contém data de entrega via HTML)

## Arquivos relevantes
| Arquivo | O que faz |
|---------|-----------|
| `api/services/sync_service.py` | Sync de monitor.db → study.db com filtro de course_ids + publication_date |
| `api/routers/activities.py` | GET `/activities/vigent` com filtros `due_date_before`/`due_date_after` |
| `api/routers/sync.py` | POST `/sync` lê course_ids do config.yaml |
| `frontend/src/components/activities/ActivityList.tsx` | Lista com filtro `due_date_after=today`, fallback para publication_date |
| `frontend/src/pages/ActivitiesPage.tsx` | Botão Sync + ActivityList |
| `src/scraper/models.py` | Schema de dados extraídos do Moodle |
| `src/scraper/html_parser.py` | Parser HTML para extrair dados do Moodle |
| `src/scraper/api_client.py` | Cliente API REST do Moodle |
