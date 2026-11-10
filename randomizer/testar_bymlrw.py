import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
sys.path.insert(0, os.path.dirname(__file__))
import ootlib as L
import bymlrw as B
L.set_game(r"D:/Ocarina of Time/jogos/The Legend of Zelda Ocarina of Time [0400486024dec000][v131072]")

files = {}
for d in reversed(L.ROMFS_DIRS):
    root = os.path.join(d, 'Banc')
    for r, _, fs in os.walk(root):
        for f in fs:
            if f.endswith('.bcett.byml.zs'):
                files[os.path.relpath(os.path.join(r, f), d)] = os.path.join(r, f)
ok = iguais = 0
for rel, p in sorted(files.items()):
    d = L.unzs(open(p, 'rb').read())
    root, ver, E = B.load(d)
    d2 = B.dump(root, ver, E)
    root2, _, _ = B.load(d2)
    assert B.plain(root) == B.plain(root2), rel
    assert L.byml(d) == L.byml(d2), rel  # leitor antigo tambem concorda
    ok += 1
    iguais += d == d2
print(ok, 'arquivos ok;', iguais, 'byte a byte iguais ao original')
