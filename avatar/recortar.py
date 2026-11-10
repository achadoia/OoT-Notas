"""Recorta a folha 2x2 do avatar, tira o fundo verde chroma (sem comer o gorro verde) e alinha os 4 quadros.
uso: python recortar.py <folha.png> <pasta_saida>"""
import sys, os
import numpy as np
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
im = np.array(Image.open(src).convert('RGB')).astype(np.float32)
H, W, _ = im.shape
r, g, b = im[..., 0], im[..., 1], im[..., 2]

# chave = quanto o pixel se parece com o fundo. Verde chroma: G muito acima de R/B.
# Magenta (#FF00FF): R e B muito acima de G (pele/boca rosada tem R alto mas B baixo).
MAGENTA = np.median(im[:8, :8].reshape(-1, 3), axis=0)[1] < 100
green = (np.minimum(r, b) - g) if MAGENTA else (g - np.maximum(r, b))
T0, T1 = 70.0, 170.0
alpha = 1.0 - np.clip((green - T0) / (T1 - T0), 0, 1)
# despill: onde sobrou transparencia parcial, tira o excesso de verde da borda
edge = alpha < 0.999
if MAGENTA:
    spill = np.clip(np.minimum(r, b) - g - 25, 0, None) * (1 - alpha * 0.5)
    r2, g2, b2 = np.where(edge, r - spill, r), g, np.where(edge, b - spill, b)
    # borda = contorno preto misturado com magenta: segura R/B perto do G
    r2 = np.where(edge, np.minimum(r2, g + 40), r2)
    b2 = np.where(edge, np.minimum(b2, g + 40), b2)
else:
    spill = np.clip(g - np.maximum(r, b) - 25, 0, None)
    r2, g2, b2 = r, np.where(edge, g - spill * (1 - alpha * 0.5), g), b
rgba = np.dstack([r2, g2, b2, alpha * 255]).clip(0, 255).astype(np.uint8)

hw, hh = W // 2, H // 2
names = ['1-parado', '2-piscando', '3-falando', '4-falando-piscando']
quads = [rgba[y:y + hh, x:x + hw].copy() for y in (0, hh) for x in (0, hw)]
# a linha que divide a folha deixa um fio no topo dos quadros de baixo e na esquerda dos da direita
for i, q in enumerate(quads):
    if i >= 2:
        q[:6, :, 3] = 0
    if i % 2 == 1:
        q[:, :6, 3] = 0


def mask(q):
    return (q[..., 3] > 128).astype(np.float32)


# alinhamento: desloca cada quadro para casar a silhueta com o quadro 1 (busca +-12 px)
ref = mask(quads[0])
aligned = [quads[0]]
for q in quads[1:]:
    m = mask(q)
    best = (1e18, 0, 0)
    for dy in range(-12, 13):
        for dx in range(-12, 13):
            s = np.roll(np.roll(m, dy, 0), dx, 1)
            d = np.abs(s[20:-20, 20:-20] - ref[20:-20, 20:-20]).sum()
            if d < best[0]:
                best = (d, dy, dx)
    _, dy, dx = best
    print('deslocamento', dy, dx)
    aligned.append(np.roll(np.roll(q, dy, 0), dx, 1))

# area util comum (corta o que encosta na divisa do quadro) e salva
union = np.zeros(ref.shape, bool)
for q in aligned:
    union |= q[..., 3] > 8
ys, xs = np.where(union)
y0, y1, x0, x1 = max(ys.min() - 4, 0), min(ys.max() + 5, hh), max(xs.min() - 4, 0), min(xs.max() + 5, hw)
for n, q in zip(names, aligned):
    Image.fromarray(q[y0:y1, x0:x1]).save(os.path.join(out, n + '.png'))
# previa sobre fundo magenta para conferir o recorte
prev = Image.new('RGBA', ((x1 - x0) * 4, y1 - y0), (40, 40, 48, 255))
for i, q in enumerate(aligned):
    prev.alpha_composite(Image.fromarray(q[y0:y1, x0:x1]), (i * (x1 - x0), 0))
prev.convert('RGB').save(os.path.join(out, '_previa.png'))
print('ok', x1 - x0, 'x', y1 - y0)
