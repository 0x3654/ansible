# homelab

Базовая роль хоста homelab-группы: системные пакеты, docker-репозиторий,
samba-шары (медиа + Time Machine см. роль timemachine), деплой compose-стеков
через filescopy, macOS-хелперы (applescript) для вспомогательных задач.

Медиасервер и торренты вынесены в отдельные роли (`mediaserver`, `torrent`,
`torrserver`) и вешаются на хосты своими `_role`-группами.
