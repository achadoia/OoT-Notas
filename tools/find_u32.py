"""Procura um ou mais u32 (big e little endian) em todos os arquivos do RomFS (descomprimidos, dentro de SARC).
uso: python find_u32.py 0x7001f17c [0x...]"""
import os, sys, struct
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(__file__))
import ootlib as L
import harvest as H

PATS = []


def init(vals):
    global PATS
    L.set_game(H.GAME)
    PATS = [(v, struct.pack('>I', v), struct.pack('<I', v)) for v in vals]


def scan(blob):
    return [v for v, be, le in PATS if be in blob or le in blob]


def work(path):
    try:
        raw = open(path, 'rb').read()
        if path.endswith('.zs'):
            raw = L.unzs(raw)
        hits = [(path, v) for v in scan(raw)]
        if raw[:4] == b'SARC':
            for name, sub in L.sarc(raw).items():
                if sub[:4] == b'\x28\xb5\x2f\xfd':
                    sub = L.unzs(sub)
                hits += [(path + '|' + name, v) for v in scan(sub)]
        return hits
    except Exception:
        return []


if __name__ == '__main__':
    vals = [int(a, 16) for a in sys.argv[1:]]
    L.set_game(H.GAME)
    files = []
    for d in L.ROMFS_DIRS + [os.path.join(H.GAME, 'updates', '131072', 'exefs')]:
        for root, dirs, fs in os.walk(d):
            rel = os.path.relpath(root, d).split(os.sep)[0]
            if rel in H.SKIP:
                dirs[:] = []
                continue
            files += [os.path.join(root, f) for f in fs]
    with Pool(10, initializer=init, initargs=(vals,)) as p:
        for hits in p.imap_unordered(work, files, chunksize=64):
            for path, v in hits:
                print(hex(v), os.path.relpath(path.split('|')[0], H.GAME), path.split('|')[1] if '|' in path else '', flush=True)
