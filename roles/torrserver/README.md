# torrserver

TorrServer (MatriX) — торрент-стриминг для Lampa: публичный фронт за
nginx+certbot по секретному пути (basic-auth ломает CORS), mem_limit
подобран по замерам (idle ~100 MiB). Secret-watch — реакция на смену
секрета.
