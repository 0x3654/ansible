#!/usr/bin/env python3
"""Поключевой merge двух JSON-файлов настроек (Cursor settings.json и др.).

Использование: sync-merge-json.py <auth> <secondary>

auth      — приоритетный файл (moro / роль);
secondary — подчинённый (citrus / живой файл приёмника).

Семантика (инцидент 2026-09-17: файл-уровневый pull затирал ключи плагинов):
- объединение множеств ключей на всех уровнях;
- конфликт значения → auth побеждает;
- ключи только у secondary — СОХРАНЯЮТСЯ (едут к auth);
- удаления не синкаются (как во всей схеме);
- массивы/скаляры у обоих → auth.

Оба файла перезаписываются одинаковым каноничным JSON (Cursor его принимает).
Файлы с комментариями/хвостовыми запятыми парсятся толерантно; если не вышло —
merge пропускается с ошибкой в stderr, файлы не трогаются (безопасный отказ).
"""
import json
import re
import sys


def tolerant_loads(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    out, in_str, esc = [], False, False
    for ch in text:  # снимаем // и /* */ комментарии вне строк
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            continue
        out.append(ch)
    stripped = "".join(out)
    stripped = re.sub(r"//[^\n]*", "", stripped)
    stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.S)
    # хвостовые запятые вне строк: убираем перед } ]
    cleaned, in_str, esc = [], False, False
    for i, ch in enumerate(stripped):
        if in_str:
            cleaned.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        if ch == "," and stripped[i + 1 : i + 30].lstrip()[:1] in ("}", "]"):
            continue
        cleaned.append(ch)
    return json.loads("".join(cleaned))


def merge(a, b):
    """union ключей; конфликт → a (auth)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = merge(a[k], v) if k in a else v
        return out
    return a


def main():
    pa, pb = sys.argv[1], sys.argv[2]
    try:
        a = tolerant_loads(open(pa, encoding="utf-8").read()) if __import__("os").path.exists(pa) else None
        b = tolerant_loads(open(pb, encoding="utf-8").read()) if __import__("os").path.exists(pb) else None
    except Exception as e:  # noqa: BLE001 — безопасный отказ
        print(f"SKIP: не распарсился JSON ({e}); файлы не тронуты", file=sys.stderr)
        sys.exit(1)
    if a is None and b is None:
        print("SKIP: оба файла отсутствуют", file=sys.stderr)
        sys.exit(1)
    merged = merge(a, b) if (a is not None and b is not None) else (a if a is not None else b)
    text = json.dumps(merged, ensure_ascii=False, indent=4) + "\n"
    for p, orig in ((pa, a), (pb, b)):
        if orig is None or json.dumps(orig, ensure_ascii=False, sort_keys=True) != json.dumps(
            merged, ensure_ascii=False, sort_keys=True
        ):
            open(p, "w", encoding="utf-8").write(text)
            print(f"MERGED {p}")
        else:
            print(f"unchanged {p}")


if __name__ == "__main__":
    main()
