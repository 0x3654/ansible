#!/usr/bin/env python3
"""Разовый harvest инбаунд-материала из панельной sqlite 3x-ui в vault-словарь.

Переносит то, что жило только в x-ui.db (uuid, subId, Reality-ключи,
shortIds, порты), в аддитивную секцию `xray:` существующей записи
three_ui_servers[domain]. Формат словаря не меняет: старые ключи и все
потребители (firewall, агрегатор подписок) остаются как были.

Запуск на эталонной машине (moro):
    harvest_3xui_keys.py <domain_name>

git-операций НЕ делает: коммит inventory-сабмодуля - руками, осознанно.
Плейнтекст существует секунды (расшифровка во временный файл).
"""
import json
import os
import subprocess
import sys
import tempfile

import yaml

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SECRETS = os.path.join(REPO, "inventory/group_vars/vps/secrets.yml")
DB = "/server/vpnserver/3x-ui/db/x-ui.db"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, cwd=REPO, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, **kw)


def harvest(domain):
    sql = ("select port, settings, stream_settings from inbounds where id=1;")
    res = run(["ssh", "-o", "ConnectTimeout=10", domain,
               f"sqlite3 -json {DB} \"{sql}\""])
    rows = json.loads(res.stdout)
    if not rows:
        sys.exit(f"no inbound found in {DB} on {domain}")
    row = rows[0]
    settings = json.loads(row["settings"])
    stream = json.loads(row["stream_settings"])
    client = settings["clients"][0]
    reality = stream["realitySettings"]
    public = (reality.get("settings") or {}).get("publicKey")
    if not public:
        sys.exit("no publicKey in realitySettings.settings - panel DB too old, "
                 "derive it manually (xray x25519 -i <privateKey>)")
    return {
        "client_id": client["id"],
        "sub_id": client["subId"],
        "inbound_port": row["port"],
        "client_port": row["port"],
        "reality_server_name": reality["serverNames"][0],
        "reality_target": reality.get("target") or reality.get("dest"),
        "reality_private_key": reality["privateKey"],
        "reality_public_key": public,
        "reality_short_ids": reality["shortIds"],
    }


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: harvest_3xui_keys.py <domain_name>")
    domain = sys.argv[1]
    xray = harvest(domain)

    with tempfile.NamedTemporaryFile("w+", dir=REPO, suffix=".yml", delete=False) as tmp:
        tmppath = tmp.name
    try:
        run(["ansible-vault", "decrypt", "--output", tmppath, SECRETS])
        with open(tmppath) as fh:
            data = yaml.safe_load(fh) or {}
        entry = data.setdefault("three_ui_servers", {}).get(domain)
        if not entry:
            sys.exit(f"{domain} not found in three_ui_servers - new-host flow, "
                     "no harvest needed")
        entry["xray"] = xray
        with open(tmppath, "w") as fh:
            yaml.safe_dump(data, fh, allow_unicode=True, default_flow_style=False, sort_keys=True)
        run(["ansible-vault", "encrypt", "--encrypt-vault-id", "default", tmppath])
        os.chmod(tmppath, 0o644)
        os.replace(tmppath, SECRETS)
    finally:
        if os.path.exists(tmppath):
            os.unlink(tmppath)

    print(f"harvested {domain}: uuid={xray['client_id'][:8]}… "
          f"sub_id={xray['sub_id'][:6]}… sni={xray['reality_server_name']} "
          f"port={xray['inbound_port']} short_ids={len(xray['reality_short_ids'])}")
    print("commit inventory submodule manually")


if __name__ == "__main__":
    main()
