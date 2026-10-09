# common

Переиспользуемые задачи для других ролей (напрямую не применяется, вызываются
через include/import): apt (dist-upgrade, пакеты, docker-репозиторий,
compose_command), filescopy (рекурсивный деплой files/ с .j2 и хендлерами
down/up), firewall (idempotent iptables), certbot (standalone SSL),
nginx, telegram-notify.
