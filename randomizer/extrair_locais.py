"""Inventario dos locais randomizaveis (baus) -> data/rando_locais.json.
Um local = um ator de bau (Hash). O mesmo Hash nos arquivos Child e Adult e o mesmo bau."""
import os, sys, json, re
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import modfs as M
L = M.L

locais = {}
for d in reversed(L.ROMFS_DIRS):
    base = os.path.join(d, 'Banc')
    for r, _, fs in os.walk(base):
        for f in fs:
            if not f.endswith('.bcett.byml.zs'):
                continue
            rel = os.path.relpath(os.path.join(r, f), d).replace('\\', '/')
            area = rel.split('/')[1]
            m = re.search(r'_(Child|Adult)_', f)
            idade = m.group(1) if m else 'Ambas'
            by = L.byml(L.unzs(open(os.path.join(r, f), 'rb').read()))
            for a in by.get('Actors', []) or []:
                dyn = a.get('Dynamic') or {}
                if 'TBox' not in a['Gyaml'] or 'Drop__DropActor' not in dyn:
                    continue
                h = a['Hash']
                loc = locais.setdefault(h, {'hash': h, 'area': area, 'gyaml': a['Gyaml'], 'arquivos': [],
                                            'idades': [], 'item': dyn['Drop__DropActor'],
                                            'evento': dyn.get('GetEventName'),
                                            'sala': dyn.get('DefaultDungeonRoomIndex'),
                                            'repetivel': bool(dyn.get('IsEnableRepeatOpen')),
                                            'check': dyn.get('Drop__CheckActor'),
                                            'substituto': dyn.get('Drop__DropActor_Substitute'),
                                            'pos': a.get('Translate')})
                if rel not in loc['arquivos']:
                    loc['arquivos'].append(rel)
                if idade not in loc['idades']:
                    loc['idades'].append(idade)
                if loc['item'] != dyn['Drop__DropActor']:
                    loc.setdefault('item_por_arquivo', {})[rel] = dyn['Drop__DropActor']

lista = sorted(locais.values(), key=lambda l: (l['area'], l['sala'] or 0, l['hash']))
json.dump(lista, open(r'D:\OoT-Notas\data\rando_locais.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(lista), 'baus unicos')
print('por idade:', Counter('/'.join(sorted(l['idades'])) for l in lista))
print('repetiveis (minigame):', sum(l['repetivel'] for l in lista))
print('item diferente entre arquivos:', sum('item_por_arquivo' in l for l in lista))
por_area = Counter(l['area'] for l in lista)
print('por area:', dict(sorted(por_area.items())))
