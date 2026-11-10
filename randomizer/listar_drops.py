"""Lista todos os valores de Drop__DropActor (por tipo de ator) e os GetEventName dos baus."""
import sys, os
from collections import Counter, defaultdict
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

por_ator = defaultdict(Counter)
eventos = []
for rel, p in sorted(files.items()):
    by = L.byml(L.unzs(open(p, 'rb').read()))
    for a in by.get('Actors', []) or []:
        dyn = a.get('Dynamic') or {}
        if 'Drop__DropActor' in dyn:
            g = a['Gyaml']
            por_ator[g][dyn['Drop__DropActor']] += 1
            if 'TBox' in g and 'GetEventName' in dyn:
                eventos.append((rel.split(os.sep)[1], dyn['Drop__DropActor'], dyn['GetEventName'], dyn.get('Drop__CheckActor'), dyn.get('Drop__DropActor_Substitute')))
modo = sys.argv[1] if len(sys.argv) > 1 else 'itens'
if modo == 'itens':
    tot = Counter()
    for g, c in por_ator.items():
        tot.update(c)
    print('atores com Drop__DropActor:', {g: sum(c.values()) for g, c in sorted(por_ator.items(), key=lambda x: -sum(x[1].values()))})
    print()
    for item, n in sorted(tot.items()):
        onde = ','.join(sorted({g.replace('Obj_', '') for g, c in por_ator.items() if item in c}))
        print(f'{n:4d} {item:45s} {onde}')
else:
    for e in eventos:
        print(*e, sep=' | ')
