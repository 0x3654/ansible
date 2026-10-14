# backup

Контрактные локальные бэкапы. **Данные гоняет сам хост** (launchd на маке /
cron на linux, 00:30) — ansible только деплой и обновление при изменении правил.
Работает без сети; вынос копий наружу (маки = Time Machine, micro тянет с VPS) —
отдельные слои поверх.

## Как декларируется контракт

**Роль сервиса** (источник истины о своих данных):

```yaml
# roles/<service>/defaults/main.yml
backup_contract:
  role: <service>
  items:
    - {name: data, kind: bind, path: "{{ <service>_dir }}/data", retention: 7}
    - {name: db, kind: pg, container: <svc>-db, db: app, retention: 7}
    - {name: cache, kind: none, why: stateless}   # осознанно без копии
```

и последней таской роли:

```yaml
- name: Зарегистрировать бэкап-контракт
  ansible.builtin.set_fact:
    backup_role_contracts: "{{ backup_role_contracts | default({}) | combine({'<service>': backup_contract}) }}"
```

**Хост-экстра** (catch-all и всё, что не роль) — `host_vars/<host>/backup.yml`:

```yaml
backup_contracts:
  docker-volumes:
    role: docker-volumes
    dest: docker-volumes
    items: [{name: all-volumes, kind: docker-volumes, skip: "...", retention: 7}]
```

Роль `backup` ставится в deploy-плейбук **последней** (после ролей сервисов —
иначе их контракты ещё не зарегистрированы), пишет все контракты в
`~/.backups/contracts/*.json` (mac) / `/etc/opt/backup/contracts` (linux),
осиротевшие удаляет.

## Виды items (kinds)

| kind | что делает | когда |
|---|---|---|
| `bind` | tar czf каталога | файловая консистентность достаточна |
| `volume` | tar czf named volume через docker | — |
| `pg` | `docker exec pg_dump -Fc` | живая БД (тарить нельзя!) |
| `docker-volumes` | catch-all по всем именованным томам (кроме skip-regex) | страховка |
| `docker-manifest` | ps/volumes/images/networks/compose + полный inspect | снимок «что бегало» (прецедент 14.10) |
| `none` | ничего, попадает в отчёт с why | осознанно без копии |

`retention` — целыми комплектами: N свежих файлов на item. Не по файлам:
прецедент pg1c — «дамп без изменений» + пофайловая ротация = база без единой копии.

## Диагностика

- run-report: `~/backups/run-report-YYYY-MM-DD.txt` (exit 1 при любом FAIL —
  ловит класс «молча отработало вхолостую», прецедент PATH-баг 05.10)
- лог launchd: `~/backups/launchd.log`
- восстановление тома: `~/.local/bin/restore-docker-volume.sh <volume> [date]`
  (старое содержимое сохраняется как `<volume>.pre-restore`)
