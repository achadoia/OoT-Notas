import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import ootlib as L
from collections import Counter, defaultdict
L.set_game(r"D:/Ocarina of Time/jogos/The Legend of Zelda Ocarina of Time [0400486024dec000][v131072]")
gdl = L.byml(L.read('GameData/GameDataList.Product.110.byml.zs'))['Data']
b64 = {e['Hash']: e for e in gdl['Bool64bitKey']}
files = {}
for d in reversed(L.ROMFS_DIRS):
    root = os.path.join(d, 'Banc')
    for r, _, fs in os.walk(root):
        for f in fs:
            if f.endswith('.bcett.byml.zs'):
                files[os.path.relpath(os.path.join(r, f), d)] = os.path.join(r, f)
out = []
cnt = Counter(); tot = Counter()
for rel, p in sorted(files.items()):
    try:
        by = L.byml(L.unzs(open(p, 'rb').read()))
    except Exception as e:
        print('ERR', rel, e); continue
    for a in by.get('Actors', []) or []:
        g = a.get('Gyaml'); h = a.get('Hash')
        tot[g] += 1
        if h in b64:
            cnt[g] += 1
            out.append({'file': rel.replace(os.sep, "/"), 'gyaml': g, 'hash': h, 'pos': a.get('Translate'),
                        'dyn': a.get('Dynamic'), 'extra': b64[h].get('ExtraByte'), 'reset': b64[h].get('ResetTypeValue')})
json.dump(out, open(r'D:\OoT-Notas\data\banc_flags.json', 'w'), default=str)
print(len(files), 'arquivos', len(out), 'atores com flag de', len(b64))
for g, n in cnt.most_common(120):
    print(n, g)
