#!/usr/bin/env python3
"""Секционный union-merge md-файлов Claude между маками.

Использование: sync-merge-md.py <dir_live> <dir_staging>

dir_live   — живой ~/.claude машины A (moro);
dir_staging — копии файлов с машины B (citrus), притянутые rsync'ом.

Файлы (CLAUDE.md, CLAUDE-CHANGELOG.md) правятся параллельными сессиями на обеих
машинах — mtime-LWW молча терял бы записи/правила. Мердж: секции по заголовкам
'#'/'##', внутри — union строк с дедупом по точному совпадению; результат пишется
в ОБА каталога, затем rsync staging→B довозит его до второй машины.

Свойства: append-only записи сливаются без потерь; правка одной и той же строки
даёт видимый дубль (разруливается руками) — лучше, чем тихая потеря.
"""
import os
import sys

FILES = ["CLAUDE.md", "CLAUDE-CHANGELOG.md"]


def parse_sections(text):
    """(preamble, [(header, [lines]), ...]); заголовок — строка, начинающаяся с #."""
    preamble, sections, cur = [], [], None
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            cur = [line.strip(), []]
            sections.append(cur)
        elif cur is None:
            preamble.append(line.strip())
        else:
            cur[1].append(line.strip())
    return preamble, sections


def merge_texts(a, b):
    pa, sa = parse_sections(a)
    pb, sb = parse_sections(b)

    pre = []
    for line in pa + pb:
        if line and line not in pre:
            pre.append(line)

    index, order = {}, []
    for header, lines in sa:
        index[header] = list(lines)
        order.append(header)
    for header, lines in sb:
        if header in index:
            merged = index[header]
            for line in lines:
                if line and line not in merged:
                    merged.append(line)
        else:
            index[header] = list(lines)
            order.append(header)

    out = list(pre)
    for header in order:
        if out:
            out.append("")
        out.append(header)
        out.extend(line for line in index[header] if line)
    return "\n".join(out) + "\n"


def main():
    live, staging = sys.argv[1], sys.argv[2]
    for name in FILES:
        p_live = os.path.join(live, name)
        p_st = os.path.join(staging, name)
        a = open(p_live, encoding="utf-8").read() if os.path.exists(p_live) else None
        b = open(p_st, encoding="utf-8").read() if os.path.exists(p_st) else None
        if a is None and b is None:
            continue
        if a == b:
            print(f"unchanged {name}")
            continue
        merged = merge_texts(a or "", b or "")
        open(p_live, "w", encoding="utf-8").write(merged)
        open(p_st, "w", encoding="utf-8").write(merged)
        print(f"MERGED {name}")


if __name__ == "__main__":
    main()
