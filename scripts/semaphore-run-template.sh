#!/bin/sh
# Запуск шаблона Semaphore по расписанию (launchd/cron) без пароля на диске:
# креды читаются из env контейнера (docker inspect — легитимный источник),
# задача создаётся через REST. Пример: ./semaphore-run-template.sh 16
#
# Ночной синк маков (sync-macs): launchd-агент local.semaphore.sync-macs
# (plist в playbooks/files/sync-macs.plist) зовёт этот скрипт в 06:23.
set -eu

TPL="${1:?usage: semaphore-run-template.sh <template_id>}"
PORT="${SEMAPHORE_PORT:-3210}"

PASS=$(docker inspect semaphore --format '{{range .Config.Env}}{{println .}}{{end}}' \
       | sed -n 's/^SEMAPHORE_ADMIN_PASSWORD=//p')
[ -n "$PASS" ] || { echo "SEMAPHORE_ADMIN_PASSWORD не найден в env контейнера" >&2; exit 1; }

JAR=$(mktemp); trap 'rm -f "$JAR"' EXIT
curl -sf -c "$JAR" -X POST "http://localhost:$PORT/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"auth\":\"admin\",\"password\":\"$PASS\"}" >/dev/null

# 201 + json задачи = успешно поставлена в очередь
curl -sf -b "$JAR" -X POST "http://localhost:$PORT/api/project/1/tasks" \
  -H 'Content-Type: application/json' \
  -d "{\"template_id\": ${TPL}}"
echo
