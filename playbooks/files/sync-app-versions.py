#!/usr/bin/env python3
"""План обновлений общих приложений по версиям из Contents/Info.plist.

Использование: sync-app-versions.py <src.tsv> <dst.tsv> [exclude,comma]

tsv-файлы (собираются на машинах): имя\tверсия\tкаталог (/Applications или ~/Applications).
Версия — CFBundleShortVersionString, '?' если plist не отдал.

Вывод (по одной строке на приложение, есть в ОБОИХ машинах):
  UPDATE<TAB>имя<TAB>каталог_на_источнике   — версия источника новее, обновить
  SKIP<TAB>имя<TAB>причина                  — same/new-app/no-version/older/excluded/readonly

Новые (отсутствующие на приёмнике) приложения здесь НЕ рассматриваются —
ими занимается фаза разницы. Кастом-билды ловятся сменой версии: локальная
сборка с bumped-версией едет на другую машину, пока встречная не соберёт ещё новее.
"""
import os
import re
import sys


def load(path):
    apps = {}
    for line in open(path, encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) == 3 and parts[0]:
            apps[parts[0]] = (parts[1], parts[2])
    return apps


def vkey(v):
    """Ключ сравнения версий: числовые сегменты численно, нечисловые — лексически."""
    key = []
    for p in re.split(r"[.\-+]", v):
        if p.isdigit():
            key.append((1, int(p), ""))
        else:
            key.append((0, 0, p.lower()))
    return key


def main():
    src = load(sys.argv[1])
    dst = load(sys.argv[2])
    excl = {e.strip() for e in sys.argv[3].split(",")} if len(sys.argv) > 3 and sys.argv[3] else set()

    for name, (sv, spdir) in src.items():
        if name in excl:
            print(f"SKIP\t{name}\texcluded")
        elif name not in dst:
            print(f"SKIP\t{name}\tnew-app")  # фаза разницы этим занимается
        elif sv == "?" or dst[name][0] == "?":
            print(f"SKIP\t{name}\tno-version")
        elif sv == dst[name][0]:
            print(f"SKIP\t{name}\tsame")
        elif vkey(sv) > vkey(dst[name][0]):
            dst_app = os.path.join(dst[name][1], name + ".app")
            if not os.access(dst_app, os.W_OK):
                print(f"SKIP\t{name}\treadonly")
            else:
                print(f"UPDATE\t{name}\t{spdir}")
        else:
            print(f"SKIP\t{name}\tolder")  # на приёмнике новее — поедет встречным направлением


if __name__ == "__main__":
    main()
