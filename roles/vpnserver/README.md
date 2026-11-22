# vpnserver

Роль разворачивает VPN-сервер на чистом xray-core (Reality-инбаунд + статическая
подписка) на хостах группы `vpnserver_role`, плюс обвязку: certbot, fail2ban,
gateway-камуфляж, опциональную SNI-дверь, WARP-прокси убран (панельная эпоха).

## Два бэкенда

- `vpnserver_backend: xray` (целевой) - конфиг и подписка рендерятся из
  vault-словаря, панель не нужна вовсе
- `vpnserver_backend: panel` (легаси-откат) - 3x-ui по старой схеме; флот
  мигрирует по одному хосту, es последним

## Vault-словарь three_ui_servers (формат не менялся)

Персональные данные хоста живут в `inventory/group_vars/vps/secrets.yml`
(сабмодуль inventory, ansible-vault). Существующие записи панельной эпохи
работают как раньше; материал xray живёт в **аддитивной секции `xray:`**:

```yaml
three_ui_servers:
  <домен>:
    server_info: {location: …}
    subscription:
      suburl: …       # БАЗА (порт/путь) - её потребляет агрегатор подписок;
                      # ru2 живёт вне агрегатора на своём втором адресе -
                      # намеренно, в SERVERS его нет
      suburlid: …     # полная ссылка клиента (база + subId); у легаси-записей
                      # (ae) полная ссылка лежит прямо в suburl, suburlid нет
      subJsonPath: …  # совместимость, JSON-подписка не рендерится
    xray:            # добавлено, только для backend=xray
      client_id: …            # uuid клиента
      sub_id: …               # первоисточник для файла подписки
      inbound_port: 8443      # порт ядра (дверь роутит 443→8443)
      client_port: 8443       # порт в ссылке клиента
      reality_server_name: …  # свой домен (SNI-политика TSPU)
      reality_target: …       # цель камуфляжа (gateway 127.0.0.1:443; серт
                              # цели обязан покрывать serverName!)
      reality_private_key / reality_public_key / reality_short_ids
```

Принципы прежние: новый хост = генерация значений и регистрация через
`scripts/add_3xui_server.py` (запускать только с main - скрипт пушит main);
существующий = converge из словаря каждым прогоном. Хост без секции `xray:`
при backend=xray даёт явный fail - ключи живут только в панельной sqlite,
переносится разовым `scripts/harvest_3xui_keys.py <домен>` (git-операций
внутри нет, коммит руками).

## Что рендерится (backend=xray)

- `xray/config.json` - vless + xhttp + reality, роутинг без geodata
  (private-диапазоны литеральными CIDR; геодату образ не возит)
- `sub/nginx.conf` + `sub/webroot/<sub_path>/<sub_id>` - статическая подписка
  на панель-совместимом URL: тот же порт/путь/subId, base64(vless-link),
  заголовки Profile-Title `0x3654.com` и Profile-Update-Interval 1ч
  (панельный паритет; переменные `vpnserver_sub_title/update_interval`).
  ВАЖНО: после base64 - ни байта (lua-агрегатор строго декодирует)
- легаси-контейнер 3x-ui удаляется таском (держал порты), БД `./3x-ui/db`
  остаётся на хосте - откат = `vpnserver_backend: panel` + прогон

## Образы и обновления

- `vpnserver_xray_image: ghcr.io/0x3654/vpnserver-xray:latest` - свой образ
  (alpine + официальный бинарь, геодата срезана, ~62MB). Обновления без
  ручных актов: CI (`.github/workflows/build-xray-slim.yml`) по расписанию
  собирает FROM `xtls/xray-core:latest`, гоняет полный e2e (конфиг из
  ЭТОГО репо-шаблона + независимый клиент + curl сквозь туннель) и после
  зелёного пушит `:latest` + `rev-sha` + `xray-<version>`; watchtower на
  хостах сам катит (расписание часовое). Красный гейт = алерт в TG
  «флот отстал от апстрима». Откат = пин `vpnserver_xray_image` на тег
  руками на один деплой
- sub-nginx: `nginx:1.27-alpine` по дайджесту (статика, не критичен)

## Ports / топология

Ядро всегда слушает 8443: на door-хостах nginx-дверь роутит 443→8443 по SNI,
на остальных 443 занимает gateway-страница (basic-auth камуфляж = reality
target), клиенты ходят напрямую на порт xray. Firewall открывает ssh/443/
sub_port/8443(без двери).

## Хвосты

- subJsonPath в словаре остаётся для совместимости; JSON-подписка не
  рендерится (никто не потребляет)
- ru2 живёт ВНЕ агрегатора подписок отдельной ссылкой - намеренно
- Subscription-Userinfo не рендерится (счётчиков нет); агрегатор собирает
  его с панельных апстримов, пока они живы
