#!/usr/bin/env python3
"""Filter a Wiktionary Content File Export down to dictionary namespaces.

Keeps <page> blocks whose <ns> is main (0), MediaWiki (8), Template (10) or
Module (828); drops Usuario:/Wikcionario:/Apéndice:/Categoría: pages —
including the spam user pages whose runaway Lua expansions each cost 5-9
minutes during extraction (wiktwords warns "PARSING PAGE TOOK …" for them).

Usage: python3 filter_namespaces.py in.xml.bz2 out.xml.bz2
"""
import bz2
import re
import sys

KEEP_NS = {'0', '8', '10', '828'}
ns_re = re.compile(r'<ns>(-?\d+)</ns>')

src, dst = sys.argv[1], sys.argv[2]
kept = dropped = 0
page = []
in_page = False
out = bz2.open(dst, 'wt', encoding='utf-8')
with bz2.open(src, 'rt', encoding='utf-8') as f:
    for line in f:
        if in_page:
            page.append(line)
            if '</page>' in line:
                m = ns_re.search(''.join(page))
                if m and m.group(1) in KEEP_NS:
                    out.write(''.join(page))
                    kept += 1
                else:
                    dropped += 1
                page = []
                in_page = False
        elif '<page>' in line:
            in_page = True
            page = [line]
        else:
            out.write(line)
out.close()
print(f'kept {kept} pages, dropped {dropped} pages')
