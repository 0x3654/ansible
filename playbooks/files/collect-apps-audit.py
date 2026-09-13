#!/usr/bin/env python3
"""Аудит дрейфа приложений: живой /Applications против списков роли dotfiles.

Использование: collect-apps-audit.py <путь к roles/dotfiles/defaults/main.yml>

Отчёт:
  1) установлено, но НЕ покрыто brew-casks / MAS-списком роли (кандидаты добавить);
  2) cask'и brew, отсутствующие в списке роли (фактическая установка мимо списка);
  3) из списка роли не установлено (эталон неполный/устарел).

Apple-системные приложения и известные ручные (custom-сборки) отфильтрованы.
"""
import json
import os
import re
import subprocess
import sys

# Ручные/custom/системные — не дрейф
MANUAL = {
    # Apple ставит сама / системное
    "Safari", "Calculator", "Calendar", "Contacts", "FaceTime", "Finder", "Freeform",
    "Home", "Image Capture", "Mail", "Maps", "Messages", "Music", "News", "Notes",
    "Photo Booth", "Photos", "Podcasts", "Preview", "QuickTime Player", "Reminders",
    "Stickies", "System Settings", "TextEdit", "TV", "Font Book", "Chess", "Grapher",
    "Digital Color Meter", "Screen Sharing", "VoiceMemos", "Automator", "Books",
    "App Store", "Launchpad", "Mission Control", "Screenshot", "Widgets", "Dickens",
    # свои сборки / ставится ролью отдельно / приватный слой
    "BetterOSD", "language-handler", "Яндекс Музыка",  # мод-сборка — приватный слой
    "PulseSync", "Lampa - Каталог фильмов и сериалов", "Transmission Remote GUI",
    "Telegram QT", "oMLX", "DynamicNotch",              # свои форки: release-таски (2026-09-13)
    "Semaphore", "Semaphore local",
    # личное Steam / лаунчеры — восстанавливает сам Steam
    "Steam", "GameHub", "Heroic", "Factorio", "FTL Faster Than Light",
    "Into the Breach", "Prison Architect", "Door Kickers 2",
    # сайтовые .dmg без brew/MAS — ручная установка (чеклист восстановления)
    "МТС Линк", "Yandex.Telemost",
    # без brew-токена, решение «оставить в pro вручную» (2026-09-13)
    "Keyboop", "ANTICATER", "Pollen Count", "Pollen Forecast", "Airmine Pollen",
    "ChatGPT Classic",
    # macOS-обновляемые системные пакеты
    "Install macOS Sonoma", "Install macOS Sequoia", "Install macOS Tahoe",
}


def sh(cmd):
    env = dict(os.environ, PATH="/opt/homebrew/bin:" + os.environ.get("PATH", ""))
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env).stdout
    except Exception:
        return ""


def load_role_lists(defaults_path):
    text = open(defaults_path, encoding="utf-8").read()
    sections = {}
    cur = None
    for line in text.splitlines():
        m = re.match(r"^(\w[\w-]*):\s*$", line)
        if m and line.startswith(("macbook_homebrew", "macbook_appstore")):
            cur = m.group(1)
            sections[cur] = []
        elif cur and line.strip().startswith("- "):
            sections[cur].append(line.strip()[2:].split("#")[0].strip())
        elif cur and (line.startswith("#") or not line.strip()):
            continue  # комментарии/пустые строки внутри секции
        elif cur:
            cur = None
    return sections


def installed_apps():
    apps = set()
    import glob
    for pat in ("/Applications/*.app", os.path.expanduser("~/Applications/*.app")):
        for p in glob.glob(pat):
            bid = sh(["plutil", "-extract", "CFBundleIdentifier", "raw", "-o", "-", p + "/Contents/Info.plist"]).strip()
            if bid.startswith("com.apple.Safari.WebApp."):
                continue  # ярлыки Safari — машинные
            apps.add(os.path.basename(p)[:-4])
    return apps


def brew_cask_apps():
    """{имя .app: cask} по установленным cask'ам."""
    out = sh(["brew", "info", "--cask", "--json=v2", "--installed"])
    mapping = {}
    try:
        for c in json.loads(out)["casks"]:
            for art in c.get("artifacts", []):
                for app in art.get("app", []) if isinstance(art, dict) else []:
                    name = app if isinstance(app, str) else app.get("path", "")
                    mapping[os.path.basename(name or "").removesuffix(".app")] = c["token"]
    except Exception:
        pass
    return mapping


def role_cask_app_names(tokens):
    """Имена .app по токенам role-списка (в т.ч. не установленным) — один brew info."""
    if not tokens:
        return set()
    out = sh(["brew", "info", "--cask", "--json=v2", *sorted(tokens)])
    try:
        names = set()
        for c in json.loads(out)["casks"]:
            for art in c.get("artifacts", []):
                for app in art.get("app", []) if isinstance(art, dict) else []:
                    name = app if isinstance(app, str) else app.get("path", "")
                    if name:
                        names.add(os.path.basename(name).removesuffix(".app"))
        return names
    except Exception:
        return set()


def mas_installed():
    out = sh(["mas", "list"])
    return {re.sub(r"\s+\(\S+\)$", "", l.split(None, 1)[1]).strip() for l in out.splitlines() if l.split(None, 1)[1:]}


def main():
    role = load_role_lists(sys.argv[1])
    role_casks = set(role.get("macbook_homebrew_casks", []))
    # MAS-список в defaults — строки вида { id: N, name: "X" }: вытащим name регэкспом
    defaults_text = open(sys.argv[1], encoding="utf-8").read()
    role_mas_names = set(re.findall(r'name:\s*"([^"]+)"', defaults_text))

    installed = installed_apps()
    brew_map = brew_cask_apps()
    mas_set = mas_installed()

    covered = set(brew_map) | mas_set | role_mas_names | role_cask_app_names(role_casks) | MANUAL
    uncovered = sorted(installed - covered)

    brew_tokens = set(brew_map.values())
    casks_not_in_role = sorted(brew_tokens - role_casks)
    role_casks_missing = sorted(c for c in role_casks if c not in brew_tokens)

    print("=== УСТАНОВЛЕНО БЕЗ ПОКРЫТИЯ (кандидаты в списки роли/приват):")
    for a in uncovered:
        print(f"  {a}")
    print("=== CASK'и brew вне списка роли:")
    for c in casks_not_in_role:
        print(f"  {c}  ({brew_map_reverse(brew_map, c)})")
    print("=== CASK'и из списка роли НЕ установлены:")
    for c in role_casks_missing:
        print(f"  {c}")


def brew_map_reverse(brew_map, token):
    for app, t in brew_map.items():
        if t == token:
            return app
    return "?"


if __name__ == "__main__":
    main()
