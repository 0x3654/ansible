#!/usr/bin/env bash
# secret-watch — детект утечки секретного пути TorrServer в nginx-логах.
# Запускается кроном (см. /etc/cron.d/torrserver-secret-watch), инкрементален
# по номеру строки (переживает ротацию лога).
#
# Триггеры:
#   ALARM — запрос к /torr*, НЕ совпавший с секретом, со статусом != 404
#           (кто-то попал мимо 404 — утечка или перебор)
#   INFO  — новый IP на секретном пути (устройство сменило адрес — или чужой)
set -u

ENV_FILE="${ENV_FILE:-/server/torrserver/secret-watch.env}"
[ -r "$ENV_FILE" ] && . "$ENV_FILE"            # BOT_TOKEN= CHAT_ID= SECRETPATH=
LOG="${LOG:-/var/log/nginx/access.log}"
STATE="${STATE:-/server/torrserver/.secret-watch.state}"
IPS="${IPS:-/server/torrserver/.secret-watch.ips}"

[ -n "${SECRETPATH:-}" ] || { echo "SECRETPATH not set" >&2; exit 1; }
mkdir -p "$(dirname "$STATE")"
touch "$IPS"

prev=0
[ -r "$STATE" ] && prev=$(cat "$STATE")
now=$(wc -l < "$LOG" 2>/dev/null || echo 0)
now=${now:-0}
case "$now" in ''|*[!0-9]*) echo 0 > "$STATE"; exit 0 ;; esac
[ "$now" -eq 0 ] && [ ! -s "$LOG" ] && { echo 0 > "$STATE"; exit 0; }

# захват новых строк; если лог стал короче — была ротация: хвост .1 + весь текущий
if [ "$now" -lt "$prev" ]; then
  new=$({ tail -n "$prev" "$LOG.1" 2>/dev/null; cat "$LOG"; } )
else
  if [ "$prev" -gt 0 ]; then
    new=$(sed -n "$((prev + 1)),\$p" "$LOG")
  else
    new=$(cat "$LOG")
  fi
fi
echo "$now" > "$STATE"

alarms=""
infos=""
while IFS= read -r line; do
  [ -z "$line" ] && continue
  uri=$(printf '%s' "$line" | awk '{print $7}')
  case "$uri" in
    "/$SECRETPATH"|"/$SECRETPATH/"*)
      ip=$(printf '%s' "$line" | awk '{print $1}')
      if ! grep -qxF "$ip" "$IPS"; then
        printf '%s\n' "$ip" >> "$IPS"
        ua=$(printf '%s' "$line" | awk -F'"' '{print $6}')
        infos+="новый IP на секретном пути: ${ip} (${ua:-нет UA})"$'\n'
      fi
      ;;
    /torr*)
      status=$(printf '%s' "$line" | awk '{print $9}')
      if [ "$status" != "404" ]; then
        alarms+="чужое попадание (не 404): ${line}"$'\n'
      fi
      ;;
  esac
done <<< "$new"

msg=""
[ -n "$alarms" ] && msg+="🚨 torrserver ru2: подозрение на утечку секрета"$'\n'"$alarms"
[ -n "$infos" ]  && msg+="ℹ️ torrserver ru2: новые IP на секретном пути"$'\n'"$infos"

# api.telegram.org с сети ru2 недоступен (хостер дропает A-запись, IPv6 не
# маршрутизируется) — шлём релеем через ae2 по ssh; токен и chat уходят
# по stdin, в argv удалённого curl попадает только при его запуске
tg_send() {
  {
    printf '%s\n%s\n' "${BOT_TOKEN}" "${CHAT_ID}"
    printf '%s' "$1"
  } | ssh -i "${TG_RELAY_KEY:-/root/.ssh/torrserver_tg_relay}" \
      -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new \
      "root@${TG_RELAY_HOST:-ae2.0x3654.com}" \
      'read -r BT; read -r CI; curl -sf --max-time 15 -X POST "https://api.telegram.org/bot${BT}/sendMessage" -d chat_id="${CI}" --data-urlencode "text=$(cat)"' \
      >/dev/null 2>&1
}

if [ -n "$msg" ]; then
  if [ -n "${BOT_TOKEN:-}" ] && [ -n "${CHAT_ID:-}" ]; then
    tg_send "$msg" || echo "[ERROR] не удалось отправить в TG оба IP" >&2
  else
    echo "[WARN] TG не настроен, событие не отправлено:" >&2
    printf '%s' "$msg" >&2
  fi
fi
