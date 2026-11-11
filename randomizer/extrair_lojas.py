"""Inventario das vitrines das lojas (atores Shop_<item> nas cenas) -> data/rando_lojas.json.
Uma vitrine = um Hash; o mesmo Hash aparece nos arquivos de cada idade/variante. Mascaras (emprestimo) ficam de fora."""
import os, sys, json, re
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
import modfs as M
L = M.L

vit = {}
deku = []
for d in reversed(L.ROMFS_DIRS):
    base = os.path.join(d, 'Banc')
    for r, _, fs in os.walk(base):
        for f in fs:
            if not f.endswith('.bcett.byml.zs'):
                continue
            rel = os.path.relpath(os.path.join(r, f), d).replace(os.sep, '/')
            area = rel.split('/')[1]
            m = re.search(r'_(Child|Adult)_', f)
            idade = m.group(1) if m else 'Ambas'
            by = L.byml(L.unzs(open(os.path.join(r, f), 'rb').read()))
            for a in by.get('Actors', []) or []:
                g = a['Gyaml']
                dyn = a.get('Dynamic') or {}
                for k in ('ScrubBusiness_ShopItemActorName0', 'ScrubBusiness_ShopItemActorName1',
                          'ScrubBusiness_ShopItemActorName2'):
                    if dyn.get(k):
                        deku.append((rel, a['Hash'], k, dyn[k]))
                if not g.startswith('Shop_') or 'ShopItemIndex' not in dyn:
                    continue
                v = vit.setdefault(a['Hash'], {'hash': a['Hash'], 'area': area, 'gyaml': g, 'indice': dyn['ShopItemIndex'],
                                               'arquivos': [], 'idades': []})
                if rel not in v['arquivos']:
                    v['arquivos'].append(rel)
                if idade not in v['idades']:
                    v['idades'].append(idade)
                if v['gyaml'] != g:
                    v.setdefault('gyaml_por_arquivo', {})[rel] = g
json.dump(deku, open(r'D:\OoT-Notas\data\rando_deku.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(len(deku), 'mercadorias de Deku vendedores')
lista = sorted(vit.values(), key=lambda v: (v['area'], v['indice'], v['hash']))
json.dump(lista, open(r'D:\OoT-Notas\data\rando_lojas.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(lista), 'vitrines;', Counter(v['area'] for v in lista))
print('gyaml muda entre arquivos:', sum('gyaml_por_arquivo' in v for v in lista))
for v in lista: print(v['area'], v['indice'], v['gyaml'], v['idades'], len(v['arquivos']))
