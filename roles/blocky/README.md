# blocky

Локальный DoH-резолвер для хоста micro: не зависит от перехвата 53-го порта
на роутере (перехваченный LAN-DNS уходит в dnsmasq→AdGuardHome, blocky
работает параллельно по DoH). Upstream'ы DoH по голым IP: без bootstrap-DNS
и вне досягаемости перехвата.
