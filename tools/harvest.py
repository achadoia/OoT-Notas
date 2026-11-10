"""Varre o romfs atras de strings, aplica murmur3 e casa com os hashes do GameDataList.
Saida: D:\\OoT-Notas\\data\\names.json  {hash: nome}"""
import os, re, sys, json, mmh3
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(__file__))
import ootlib as L

GAME = r"D:/Ocarina of Time/jogos/The Legend of Zelda Ocarina of Time [0400486024dec000][v131072]"
SKIP = {'Tex', 'Model', 'Sound', 'Voice', 'Shader', 'Movie', 'TerrainArc', 'Bake', 'PreComputedCulling',
        'Font2', 'Layout2Shader', 'VolumeStats', 'Foliage'}
RX = re.compile(rb'[A-Za-z0-9_.\-/]{3,160}')
RX16 = re.compile(rb'(?:[A-Za-z0-9_.\-/]\x00){3,160}')
OUT = r"D:\OoT-Notas\data"


def strings(data):
    out = set()
    for m in RX.finditer(data):
        out.add(m.group().decode('ascii'))
    for m in RX16.finditer(data):
        out.add(m.group().decode('utf-16le'))
    return out


def expand(ss):
    res = set()
    for s in ss:
        res.add(s)
        for sep in '/.':
            if sep in s:
                parts = s.split(sep)
                res.update(parts)
                res.add(parts[-1].split('.')[0])
    return res


def work(path):
    try:
        raw = open(path, 'rb').read()
        if path.endswith('.zs'):
            raw = L.unzs(raw)
        ss = strings(raw)
        if raw[:4] == b'SARC':
            for name, sub in L.sarc(raw).items():
                ss.add(name)
                ss |= strings(L.unzs(sub) if sub[:4] == b'\x28\xb5\x2f\xfd' else sub)
        ss.add(os.path.basename(path))
        return expand(ss)
    except Exception as e:
        return {'__ERR__' + path + ':' + str(e)[:80]}


def init():
    L.set_game(GAME)


def main():
    L.set_game(GAME)
    gdl = L.byml(L.read('GameData/GameDataList.Product.110.byml.zs'))['Data']
    want = {}
    for t, lst in gdl.items():
        for e in lst:
            if t != 'Bool64bitKey':
                want[e['Hash']] = t
    files = []
    for d in L.ROMFS_DIRS + [os.path.join(GAME, 'updates', '131072', 'exefs'), os.path.join(GAME, 'base', 'exefs')]:
        for root, dirs, fs in os.walk(d):
            rel = os.path.relpath(root, d).split(os.sep)[0]
            if rel in SKIP:
                dirs[:] = []
                continue
            files += [os.path.join(root, f) for f in fs]
    print(len(files), 'arquivos', len(want), 'hashes', flush=True)
    found, allstr, errs = {}, set(), []
    with Pool(10, initializer=init) as p:
        for i, ss in enumerate(p.imap_unordered(work, files, chunksize=64)):
            for s in ss:
                if s.startswith('__ERR__'):
                    errs.append(s); continue
                allstr.add(s)
            if i % 20000 == 0:
                print(i, len(allstr), flush=True)
    for s in allstr:
        h = mmh3.hash(s, 0, signed=False)
        if h in want:
            found[h] = s
    os.makedirs(OUT, exist_ok=True)
    json.dump({str(k): v for k, v in sorted(found.items(), key=lambda x: x[1])}, open(os.path.join(OUT, 'names.json'), 'w'), indent=0)
    open(os.path.join(OUT, 'strings.txt'), 'w', encoding='utf-8').write('\n'.join(sorted(allstr)))
    print('erros', len(errs), errs[:5])
    from collections import Counter
    c = Counter(want[h] for h in found)
    tot = Counter(want.values())
    for t in tot:
        print(t, c[t], '/', tot[t])


if __name__ == '__main__':
    main()
