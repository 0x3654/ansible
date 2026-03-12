# Ansible Infrastructure

> Управление инфраструктурой: VPS-серверы, homelab, MacBook, GISP-стек.
> Docker Compose на всех хостах, деплой через Ansible, расписания через Semaphore CI.

---

## Быстрый старт

```bash
git clone --recurse-submodules <repo>
cd ansible
ansible-galaxy install -r requirements.yml

# Секреты для нужных ролей
cp roles/<role>/vars/secrets.yml.example roles/<role>/vars/secrets.yml
```

**Требования:** Ansible 2.9+, SSH-доступ к хостам. Python 3 на целевых хостах устанавливается через `make init-new-server`.

---

## Запуск

```bash
make deploy            # полный деплой — динамически собирает роли по inventory-группам (см. ниже)
make deploy h={host}   # конкретные хосты
make deploy-vps        # только VPS
make gisp              # деплой GISP стека
make semaphore         # деплой Semaphore CI
make manage            # управление серверами
make restart h=micro   # перезапуск сервисов
make certbot           # обновление SSL
make diskspace-cleanup # обслуживание диска
make init-new-server   # первичная настройка нового сервера
make fix-dns           # правка DNS
make cleanup           # очистка
```

Отладка: `make deployv` — полный вывод, `make deploy-check` — dry-run.

### Как работает `make deploy`

`playbooks/deploy.yml` не содержит фиксированного списка ролей — всё собирается динамически:

1. **Сканирует `roles/`** — находит все директории через `find`
2. **Подгружает vars** — для каждой роли включает `vars/main.yml` и `vars/secrets.yml` (ошибки игнорируются — файл просто отсутствует)
3. **Подгружает `host_vars/<hostname>.yml`**
4. **Для каждой роли** — проверяет, есть ли текущий хост в группе `<role>_role` в inventory. Если да — применяет роль

Принадлежность хоста к роли определяется в `inventory.yml` через специальные группы:

```yaml
gisp_role:
  hosts:
    micro:

vpnserver_role:
  hosts:
    ae:
    ae2:
    es:
```

Добавить хост в роль = добавить его в нужную `_role`-группу. Плейбук подхватит автоматически, без правки плейбука.

---

## Структура

```
ansible/
├── inventory/          # субмодуль (приватный): prod + dev inventory
├── inventory_example/  # пример структуры inventory (для форка/онбординга)
├── host_vars/          # переменные per-host
├── playbooks/          # плейбуки
├── roles/
│   ├── .template/      # скаффолд для новых ролей
│   ├── common/         # переиспользуемые задачи: apt, filescopy, firewall, certbot
│   ├── gisp/           # поиск по реестру Минпромторга (micro, GPU)
│   ├── homelab/        # медиасервер, smarthome, торренты (nano)
│   ├── macbook/        # DevOps-окружение на MBA
│   ├── manage/         # обновления, обслуживание серверов
│   ├── semaphore/      # Semaphore CI (ae2)
│   ├── subnginx3xui/   # nginx-прокси для 3x-ui подписок (es)
│   ├── untilwall/      # untilwall (us2)
│   └── vpnserver/      # VPN: 3x-ui/Xray + AmnesiaWG (все VPS)
├── configs/            # конфиги 3x-ui, AWG клиентов
├── ansible.cfg
├── makefile
└── requirements.yml
```

---

## Inventory (submodule)

`inventory/` — приватный репозиторий. При изменении файлов нужно коммитить в оба репо:

```bash
cd inventory && git add . && git commit -m "..." && git push
cd .. && git add inventory && git commit -m "update inventory submodule" && git push
```

`inventory_example/` — публичный пример структуры inventory с обезличенными хостами. Показывает, как правильно объявлять группы `_role` и переменные хостов.

---

## Архитектура ролей

### `common` — общие задачи

Не применяется напрямую — другие роли вызывают её задачи через `include_role`.

| Задача | Описание |
|--------|----------|
| `apt.yml` | dist-upgrade, установка пакетов, Docker-репозиторий, определение `compose_command` |
| `filescopy.yml` | рекурсивный деплой `roles/<role>/files/` через `filetree`; `.j2`-шаблоны, `special_ownership`, down/up хендлеры |
| `firewall.yml` | idempotent iptables: добавляет нужные правила, удаляет лишние, сохраняет через `netfilter-persistent` |
| `certbot.yml` | выдаёт/обновляет SSL (standalone); открывает/закрывает порт 80; Telegram-уведомление |
| `nginx.yml` | установка и настройка nginx |
| `telegram-notify.yml` | уведомления в Telegram |

### `roles/.template` — скаффолд

Шаблон для новых ролей с готовой структурой задач и DRY-переменными в `defaults/main.yml`
(`folder_user`, `path`, `files_source_dir`, `deploy_path` выводятся из имени роли автоматически).

```bash
cp -r roles/.template roles/<new_role>
# заменить {{ role_name }} на имя роли
```

Стандартные теги: `apt` · `filescopy` · `firewall`

---

## Секреты

Роли с секретами содержат `vars/secrets.yml.example`:

```bash
cp roles/<role>/vars/secrets.yml.example roles/<role>/vars/secrets.yml
# заполнить значения
```

---

## Semaphore CI

Веб-интерфейс для запуска и расписания плейбуков.
Управляет GISP pipeline и задачами обслуживания.

Подробнее: [roles/semaphore/](roles/semaphore/)

---

## Документация по ролям

- [gisp](roles/gisp/README.md) — GISP стек: downloader → import → embeddings
- [homelab](roles/homelab/README.md) — homelab на nano
- [vpnserver](roles/vpnserver/README.md) — VPN серверы
- [macbook](roles/macbook/README.md) — DevOps-окружение на MacBook
