"""Mostra todos os campos dos atores de bau / coracao / item solto nos Banc."""
import sys, os, json
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import ootlib as L
L.set_game(r"D:/Ocarina of Time/jogos/The Legend of Zelda Ocarina of Time [0400486024dec000][v131072]")

files = {}
for d in reversed(L.ROMFS_DIRS):
    root = os.path.join(d, 'Banc')
    for r, _, fs in os.walk(root):
        for f in fs:
            if f.endswith('.bcett.byml.zs'):
                files[os.path.relpath(os.path.join(r, f), d)] = os.path.join(r, f)

want = sys.argv[1] if len(sys.argv) > 1 else 'TBox'
keys = Counter(); dynkeys = Counter(); vals = Counter()
exemplos = []
for rel, p in sorted(files.items()):
    by = L.byml(L.unzs(open(p, 'rb').read()))
    for a in by.get('Actors', []) or []:
        g = a.get('Gyaml', '')
        if want not in g:
            continue
        keys.update(a.keys())
        dyn = a.get('Dynamic') or {}
        dynkeys.update(dyn.keys())
        for k, v in dyn.items():
            if isinstance(v, (str, int, bool)):
                vals[(k, v)] += 1
        if len(exemplos) < 4:
            exemplos.append((rel, a))
print('arquivos', len(files))
print('campos do ator:', keys.most_common())
print('campos Dynamic:', dynkeys.most_common())
print('valores Dynamic mais comuns:')
for (k, v), n in vals.most_common(60):
    print(f'  {n:4d} {k} = {v}')
for rel, a in exemplos:
    print('---', rel)
    print(json.dumps(a, default=str, ensure_ascii=False)[:1500])
