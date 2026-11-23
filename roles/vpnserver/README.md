# vpnserver

Роль разворачивает VPN-сервер на чистом xray-core (Reality-инбаунд) на хостах
группы `vpnserver_role`, плюс обвязку: certbot, fail2ban, gateway-камуфляж,
опциональную SNI-дверь. Панели нет и не будет (эпоха 3x-ui закрыта
2026-11-23; история - в git).

## Конфигурация: vault-словарь three_ui_servers

Персональные данные хоста живут в `inventory/group_vars/vps/secrets.yml`
(сабмодуль inventory, ansible-vault):

```yaml
three_ui_servers:
  <домен>:
    server_info: {location: …}
    subscription:
      suburl: …       # БАЗА (порт/путь) - её потребляет агрегатор подписок
                      # на es:2097; разделение «выход/вход в РФ» - через
                      # разные subId у клиентов
      suburlid: …     # полная ссылка клиента (база + subId)
    xray:
      client_id: …            # uuid клиента
      sub_id: …               # первоисточник для файла подписки
      inbound_port: 8443      # порт ядра (дверь роутит 443→8443)
      client_port: 8443       # порт в ссылке клиента
      reality_server_name: …  # свой домен (SNI-политика TSPU)
      reality_target: …       # цель камуфляжа; серт цели обязан покрывать
                              # serverName, и цель обязана жить!
      reality_private_key / reality_public_key / reality_short_ids
```

Принципы: новый хост = генерация значений и регистрация через
`scripts/add_3xui_server.py` (запускать только с main - скрипт пушит main);
существующий = converge из словаря каждым прогоном.

## Что рендерится

- `xray/config.json` - vless + xhttp + reality, роутинг без geodata
  (private-диапазоны литеральными CIDR)
- `/var/www/vpnserver-sub/<sub_path>/<sub_id>` + `/etc/nginx/conf.d/vpnserver-sub.conf`
  - статическая подписка на том же порту/URL, что были у панели: base64(vless-link)
  без хвостового мусора после (lua-агрегатор строго декодирует), заголовки
  Profile-Title `0x3654.com` и Update-Interval 1ч (переменные роли)
- легаси-контейнер 3x-ui удаляется таском, если вдруг найдётся

## Порты / топология

Ядро всегда 8443: на door-хостах nginx-дверь роутит 443→8443 по SNI,
на остальных 443 занимает реальный сервис (vdl/torrserver) или
gateway-страницу (basic-auth камуфляж = reality target). Firewall:
ssh / 443 / sub_port / 8443 (кроме door).

## Образы и обновления

`vpnserver_xray_image: ghcr.io/0x3654/vpnserver-xray:latest` - свой образ
(alpine + официальный бинарь, геодата срезана, ~43MB). Конвейер без ручных
актов: CI (`.github/workflows/build-xray-slim.yml`) по cron каждые 6ч
собирает FROM `xtls/xray-core:latest`, гоняет полный e2e (конфиг из шаблона
этой роли + независимый клиент + curl сквозь туннель) и после зелёного
пушит `:latest` + `rev-sha` + `xray-<version>`. Watchtower (часовой) катит
хосты сам; на ru2 его нет - там обновления деплоем. Красный гейт = TG-алерт
«флот отстал от апстрима». Откат = пин `vpnserver_xray_image` на тег руками.
