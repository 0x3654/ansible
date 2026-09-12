#!/usr/bin/env python3
"""Секционный union-merge md-файлов Claude между маками (блоко-осознанный).

Использование: sync-merge-md.py <dir_live> <dir_staging>

dir_live    — живой ~/.claude машины A (moro);
dir_staging — копии файлов с машины B (citrus), притянутые rsync'ом.

CLAUDE.md и CLAUDE-CHANGELOG.md правят параллельные сессии на обеих машинах —
mtime-LWW молча терял бы записи и правки правил. Мердж: блоки по заголовкам
уровня `#`, внутри — секции `##`, внутри секций — union строк с дедупом по
точному совпадению; результат пишется в ОБА каталога, rsync staging→B довозит
его до второй машины.

Гарантии:
- новая секция с B попадает в СВОЙ блок (личное — в 🏠, рабочее — в ⛔️),
  а не в конец файла;
- append-only записи сливаются без потерь; дублированные секции/строки
  (сессии писали одно в два блока) схлопываются в одну;
- правка одной строки даёт видимый дубль (чинится руками) — лучше тихой потери;
- CLAUDE-CHANGELOG.md нормализуется: датные секции внутри блока — по убыванию
  даты (свежие сверху), стабильно.
"""
import os
import re
import sys

FILES = {"CLAUDE.md": False, "CLAUDE-CHANGELOG.md": True}
DATE_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})")


def parse_blocks(text):
    """→ (preamble, [(block_header|None, [(header, [lines]), ...]), ...])"""
    preamble, blocks, block, sec = [], [], [None, []], None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("# ") and not s.startswith("## "):
            if sec is not None:
                sec = None
            if block[0] is not None or block[1]:
                blocks.append((block[0], block[1]))
            block = [s, []]
        elif s.startswith("#"):
            sec = (s, [])
            block[1].append(sec)
        elif sec is None and not block[1] and block[0] is None:
            preamble.append(s)
        elif sec is not None:
            sec[1].append(s)
    if block[0] is not None or block[1]:
        blocks.append((block[0], block[1]))
    return preamble, blocks


def merge_blocks(a_blocks, b_blocks):
    """union блоков (по заголовку #) и их секций (по заголовку ##)."""
    index, order = {}, []  # block_header -> {sec_header: lines}; порядок блоков
    for bh, secs in a_blocks + b_blocks:
        if bh not in index:
            index[bh] = {}
            order.append(bh)
        secs_idx = index[bh]
        for sh, lines in secs:
            if sh in secs_idx:
                target = secs_idx[sh]
                for l in lines:
                    if l and l not in target:
                        target.append(l)
            else:
                secs_idx[sh] = [l for l in lines if l]
    return order, index


def sort_block_dates(headers):
    """`##`-секции блока — по убыванию даты, стабильно; без даты — в конец."""
    def key(h):
        m = DATE_RE.match(h)
        return m.group(1) if m else "0000"
    return sorted(headers, key=key, reverse=True)


def render(preamble, block_order, block_index, resort_flags):
    out = [l for l in preamble if l]
    for bh in block_order:
        secs = block_index[bh]
        headers = list(secs.keys())
        if resort_flags:
            headers = sort_block_dates(headers)
        if bh is not None:
            if out:
                out.append("")
            out.append(bh)
        for sh in headers:
            out.append("")
            out.append(sh)
            out.extend(l for l in secs[sh] if l)
    return "\n".join(out) + "\n"


def merge_text(a_text, b_text, resort):
    pa, ba = parse_blocks(a_text)
    pb, bb = parse_blocks(b_text)
    pre = [l for l in pa if l]
    for l in pb:
        if l and l not in pre:
            pre.append(l)
    order, index = merge_blocks(ba, bb)
    return render(pre, order, index, resort)


def main():
    live, staging = sys.argv[1], sys.argv[2]
    for name, resort in FILES.items():
        p_live = os.path.join(live, name)
        p_st = os.path.join(staging, name)
        a = open(p_live, encoding="utf-8").read() if os.path.exists(p_live) else None
        b = open(p_st, encoding="utf-8").read() if os.path.exists(p_st) else None
        if a is None and b is None:
            continue
        merged = merge_text(a or "", b or "", resort)
        changed = [
            path
            for path, orig in ((p_live, a), (p_st, b))
            if orig != merged
        ]
        for path in changed:
            open(path, "w", encoding="utf-8").write(merged)
        print(("MERGED " if changed else "unchanged ") + name)


if __name__ == "__main__":
    main()
