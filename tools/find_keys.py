"""Procura no RomFS em que arquivos aparecem chaves de 64 bits (big e little endian).
uso: python find_keys.py <slot progress.sav>  -> data\\keys_found.json"""
import os, sys, json, struct
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(__file__))
import ootlib as L
import harvest as H

KEYS = []


def init(keys):
    global KEYS
    L.set_game(H.GAME)
    KEYS = [(k, struct.pack('>Q', k), struct.pack('<Q', k)) for k in keys]


def scan(blob):
    return [k for k, be, le in KEYS if be in blob or le in blob]


def work(path):
    try:
        raw = open(path, 'rb').read()
        if path.endswith('.zs'):
            raw = L.unzs(raw)
        hits = [(path, k) for k in scan(raw)]
        if raw[:4] == b'SARC':
            for name, sub in L.sarc(raw).items():
                if sub[:4] == b'\x28\xb5\x2f\xfd':
                    sub = L.unzs(sub)
                hits += [(path + '|' + name, k) for k in scan(sub)]
        return hits
    except Exception:
        return []


def main():
    L.set_game(H.GAME)
    banc = {x['hash'] for x in json.load(open(os.path.join(H.OUT, 'banc_flags.json')))}
    _, keys, _ = L.read_save(sys.argv[1])
    unk = sorted(k for k in keys if k not in banc)
    files = []
    for d in L.ROMFS_DIRS:
        for root, dirs, fs in os.walk(d):
            rel = os.path.relpath(root, d).split(os.sep)[0]
            if rel in H.SKIP:
                dirs[:] = []
                continue
            files += [os.path.join(root, f) for f in fs]
    found = {}
    with Pool(10, initializer=init, initargs=(unk,)) as p:
        for hits in p.imap_unordered(work, files, chunksize=64):
            for path, k in hits:
                found.setdefault(hex(k), []).append(os.path.relpath(path.split('|')[0], H.GAME) + ('|' + path.split('|')[1] if '|' in path else ''))
    json.dump(found, open(os.path.join(H.OUT, 'keys_found.json'), 'w'), indent=1)
    print(len(unk), 'chaves desconhecidas;', len(found), 'achadas')
    for k, v in list(found.items())[:40]:
        print(k, v[:3])


if __name__ == '__main__':
    main()
