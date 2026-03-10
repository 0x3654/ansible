# GISP Role

## Description
GISP — система поиска по реестру Минпромторга с интерфейсом OpenWebUI.

Роль разворачивает стек на целевом сервере: копирует `compose.yaml`, создаёт `.env`,
подготавливает volume-директории и поднимает долгоживущие сервисы.

## Requirements
- Ansible 2.9+
- Docker + Compose plugin на целевом хосте (устанавливаются через тег `apt`)

## Role Variables

Переменные с дефолтами из `defaults/main.yml`:

### Пути и пользователь
| Переменная | Дефолт | Описание |
|-----------|--------|----------|
| `path` | `/git/gisp` | Путь к проекту на сервере |
| `folder_user` | `gisp` | Системный пользователь |

### Порты сервисов
| Переменная | Дефолт |
|-----------|--------|
| `api_port` | `8000` |
| `openwebui_port` | `3333` |
| `semantic_port` | `8010` |
| `postgres_port` | `5432` |

### PostgreSQL
| Переменная | Дефолт | Описание |
|-----------|--------|----------|
| `pg_shm_size` | `2g` | shared_memory |
| `pg_autoprewarm_interval` | `120` | Интервал авто-прогрева кэша |

### Семантический сервис
| Переменная | Дефолт | Описание |
|-----------|--------|----------|
| `semantic_workers` | `2` | Воркеры uvicorn |
| `semantic_cache_ttl_seconds` | `604800` | TTL кэша эмбеддингов (7 дней) |
| `semantic_force_seqscan` | `0` | Принудительный seqscan (отладка) |

### Импорт и downloader
| Переменная | Дефолт | Описание |
|-----------|--------|----------|
| `files_dir` | `/files` | Путь к CSV-файлам внутри контейнера |
| `max_csv_files` | `7` | Хранить N последних CSV |
| `max_log_files` | `7` | Хранить N последних лог-файлов |
| `auto_embed` | `1` | Авто-запуск embeddings после импорта |
| `start_date` | `2024-09-05` | Начальная дата для скачивания |

### Embeddings worker
| Переменная | Дефолт | Описание |
|-----------|--------|----------|
| `embeddings_batch_size` | `200` | Размер батча (fetch + HTTP + upsert) |
| `embeddings_shard_index` | `0` | Индекс шарда (для параллельного запуска) |
| `embeddings_shard_count` | `1` | Кол-во шардов |
| `force` | `0` | Пересчитать все, игнорируя кэш |
| `dry_run` | `0` | Без записи в БД |

### Переменная инвентаря (не в defaults)
| Переменная | Пример | Описание |
|-----------|--------|----------|
| `gisp_project_src` | `/git/gisp` | Путь к проекту — используется в плейбуках задач |

## Secrets

Создать `vars/secrets.yml` на основе `vars/secrets.yml.example`:

```yaml
gisp_pg_user: "registry"
gisp_pg_password: "registry"
gisp_pg_db: "registry"
gisp_telegram_bot_token: "your_token"
gisp_telegram_chat_id: "your_chat_id"
```

## Dependencies
- `common` role

## Example Playbook

```yaml
- hosts: gisp_servers
  roles:
    - role: gisp
```

## Tags
- `apt` — установка Docker + Compose plugin
- `filescopy` — деплой compose.yaml, .env, synonyms.json, webui.db
- `firewall` — открыть порт 3333

## Access
- OpenWebUI: `http://server:3333`  (login: `admin@gisp.ru` / `123`)
- API docs: `http://server:8000/docs`

---

## Task Playbooks

Задачные контейнеры **не** запускаются ролью — ими управляет Semaphore через
отдельные плейбуки. Все три плейбука требуют переменную `gisp_project_src` в инвентаре.

### `gisp-downloader.yml`
Скачивает актуальные CSV из minpromtorg.gov.ru в `./files/`.

```bash
ansible-playbook playbooks/gisp-downloader.yml -i inventory/inventory.yml
```

**Что делает:**
1. `docker compose run --rm downloader` в `{{ gisp_project_src }}`
2. При ошибке — Telegram уведомление со stdout/stderr через `scripts/send_telegram.sh`
3. Завершает с `fail` если контейнер вернул ненулевой код

**Расписание Semaphore:** ежедневно в 19:00 МСК

---

### `gisp-import.yml`
Импортирует CSV-файлы в PostgreSQL (`registry.reestr`).

```bash
ansible-playbook playbooks/gisp-import.yml -i inventory/inventory.yml
```

**Что делает:**
1. `docker compose run --rm import` в `{{ gisp_project_src }}`
2. Telegram уведомление всегда (✅ успех / ❌ ошибка) с полным логом контейнера
3. Завершает с `fail` если контейнер вернул ненулевой код

**Расписание Semaphore:** ежедневно в 00:00 МСК (после downloader в 19:00)

---

### `gisp-embeddings.yml`
Пересчитывает семантические эмбеддинги для записей реестра.

```bash
ansible-playbook playbooks/gisp-embeddings.yml -i inventory/inventory.yml
```

**Что делает:**
1. `docker compose --profile embeddings run --rm embeddings-worker`
2. Батчевая обработка: 1 HTTP запрос + 1 SQL upsert на батч из `BATCH_SIZE` записей
3. При ошибке — Telegram уведомление
4. Завершает с `fail` если контейнер вернул ненулевой код

**Расписание Semaphore:** ежедневно в 04:00 МСК (после import в 00:00)

---

### Цепочка запуска (prod)
```
19:00 downloader  →  00:00 import  →  04:00 embeddings-worker
```
CSV скачиваются вечером, импортируются ночью, эмбеддинги считаются под утро.

---

## Scheduling (Semaphore)

Расписания управляются через Semaphore (`http://server:3210`).
Каждый плейбук имеет два шаблона: `dev` и `prod`.

| Плейбук | Расписание | Хосты |
|---------|-----------|-------|
| downloader | `0 19 * * *` | dev + prod |
| import | `0 0 * * *` | dev + prod |
| embeddings | `0 4 * * *` | dev + prod |
