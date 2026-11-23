#!/bin/bash
# Разовая чистка остатков 3x-ui на хостах флота (без ролей).
# Убирает: каталог /server/vpnserver/3x-ui (панельная sqlite, WAL, gob-метрики),
# панельные образы (mhsanaei/3x-ui, teddysun/xray), осиротевший контейнер awg.
# НЕ трогает: xray, vpnserver-sub вхосты, fail2ban, certbot-сертификаты.
#
# Гард: хост чистится только если контейнер xray жив (миграция завершена).
# По умолчанию DRY-RUN; реальное удаление - флагом --apply.
#
# Usage: cleanup-3xui-leftovers.sh [--apply] [host ...]   (по умолчанию все 4)
set -uo pipefail
HOSTS=(ae ae2 es ru2)
APPLY=0
for a in "$@"; do
  case "$a" in
    --apply) APPLY=1 ;;
    *) HOSTS=("$a") ;;
  esac
done

DIR=/server/vpnserver/3x-ui
total_freed=0

for H in "${HOSTS[@]}"; do
  echo "=== $H"
  if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$H" 'docker ps --format "{{.Names}}" | grep -qx xray' 2>/dev/null; then
    echo "  SKIP: контейнер xray не запущен (миграция не завершена?) - чистить нельзя"
    continue
  fi

  if [ "$APPLY" = 0 ]; then
    echo "  [dry-run] будет удалено:"
    ssh -o BatchMode=yes "$H" "
      du -sh $DIR 2>/dev/null | sed 's/^/    каталог /'
      docker images --format '{{.Repository}}:{{.Tag}} {{.Size}}' | grep -E 'mhsanaei/3x-ui|teddysun/xray' | sed 's/^/    образ   /'
      docker ps -a --format '{{.Names}}' | grep -x awg | sed 's/^/    контейнер /'
      true"
  else
    ssh -o BatchMode=yes "$H" "
      set -e
      FREE_BEFORE=\$(df -B1 --output=avail / | tail -1)
      docker ps -a --format '{{.Names}}' | grep -x awg && docker rm -f awg >/dev/null && echo '  контейнер awg удалён'
      rm -rf $DIR && echo '  каталог 3x-ui (БД/WAL/метрики) удалён'
      docker images --format '{{.Repository}}:{{.Tag}}' | grep -E 'mhsanaei/3x-ui|teddysun/xray' | xargs -r docker rmi >/dev/null 2>&1 && echo '  панельные образы удалены'
      FREE_AFTER=\$(df -B1 --output=avail / | tail -1)
      echo \"  освобождено: \$(( (FREE_AFTER - FREE_BEFORE) / 1024 / 1024 )) MB\""
  fi
done

[ "$APPLY" = 0 ] && echo && echo "dry-run; реальная чистка: $0 --apply"
