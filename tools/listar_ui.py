"""Lista as texturas de um BNTX da UI e salva em PNG as que casam com o filtro.
uso: python listar_ui.py <rel_romfs.bntx.zs> [filtro_regex] [pasta_saida]"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import ootlib as L  # noqa: E402
import bntx  # noqa: E402

JOGO = r'D:\Ocarina of Time\jogos\The Legend of Zelda Ocarina of Time [0400486024dec000][v131072]'
L.set_game(JOGO)
rel = sys.argv[1]
pat = re.compile(sys.argv[2] if len(sys.argv) > 2 else '.', re.I)
out = sys.argv[3] if len(sys.argv) > 3 else None
raw = L.read(rel)
if raw[:4] == b'SARC':
    print('SARC:', list(L.sarc(raw).keys())[:50])
    sys.exit()
ts = bntx.textures(raw)
print('texturas:', len(ts))
for i, t in enumerate(ts):
    if pat.search(t['name']):
        print(i, t['name'], t['w'], t['h'], hex(t['fmt']))
        if out:
            os.makedirs(out, exist_ok=True)
            try:
                im, _ = bntx.decode(raw, i)
                im.save(os.path.join(out, t['name'] + '.png'))
            except Exception as e:  # noqa: BLE001
                print('  erro:', e)
