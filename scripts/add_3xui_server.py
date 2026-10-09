#!/usr/bin/env python3
"""Влить фрагмент конфига нового 3x-ui сервера в vault-словарь и закоммитить.

Запускается на эталонной машине (moro) задачей роли vpnserver при первичном
развёртывании нового VPS. Плейнтекст существует секунды: расшифровка во
временный файл, мерж, шифрование обратно, git-коммит точным pathspec.

Usage: add_3xui_server.py <domain_name> <fragment.yml>
"""
import os
import subprocess
import sys
import tempfile

import yaml

REPO = "/Users/m/code/ansible"
SECRETS = os.path.join(REPO, "group_vars/vps/secrets.yml")


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, cwd=REPO, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, **kw)


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: add_3xui_server.py <domain_name> <fragment.yml>")
    domain, fragment = sys.argv[1], sys.argv[2]

    with open(fragment) as fh:
        entry = yaml.safe_load(fh)

    # vault roundtrip: расшифровали во временный файл, обновили, зашифровали
    with tempfile.NamedTemporaryFile("w+", dir=REPO, suffix=".yml", delete=False) as tmp:
        tmppath = tmp.name
    try:
        run(["ansible-vault", "decrypt", "--output", tmppath, SECRETS])
        with open(tmppath) as fh:
            data = yaml.safe_load(fh) or {}
        data.setdefault("three_ui_servers", {})[domain] = entry
        with open(tmppath, "w") as fh:
            yaml.safe_dump(data, fh, allow_unicode=True, default_flow_style=False, sort_keys=True)
        run(["ansible-vault", "encrypt", "--encrypt-vault-id", "default", tmppath])
        os.chmod(tmppath, 0o644)
        os.replace(tmppath, SECRETS)
    finally:
        if os.path.exists(tmppath):
            os.unlink(tmppath)
    os.unlink(fragment)

    # коммит точным pathspec: чужие правки в рабочей копии не трогаем
    run(["git", "pull", "--rebase", "--autostash", "origin", "main"])
    run(["git", "add", SECRETS])
    run(["git", "commit", "-m", f"vpnserver: register {domain} in vault group_vars", "--", SECRETS])
    run(["git", "push", "origin", "HEAD:main"])
    print(f"merged and committed: {domain}")


if __name__ == "__main__":
    main()
