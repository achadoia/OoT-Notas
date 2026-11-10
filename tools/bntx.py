"""BNTX (Switch / Switch 2) -> PIL Image. So o mip 0 da primeira textura (ou todas com all_textures)."""
import struct
import numpy as np
import texture2ddecoder as t2d
from PIL import Image

# tipo (byte alto do formato) -> (bytes por bloco, bloco w, bloco h, decodificador)
FMT = {
    0x1a: (8, 4, 4, t2d.decode_bc1),
    0x1b: (16, 4, 4, None),
    0x1c: (16, 4, 4, t2d.decode_bc3),
    0x1d: (8, 4, 4, t2d.decode_bc4),
    0x1e: (16, 4, 4, t2d.decode_bc5),
    0x1f: (16, 4, 4, lambda d, w, h: t2d.decode_bc6(d, w, h)),
    0x20: (16, 4, 4, t2d.decode_bc7),
    0x0b: (4, 1, 1, None),   # R8G8B8A8
}
_ASTC = {0x2d: (4, 4), 0x2e: (5, 4), 0x2f: (5, 5), 0x30: (6, 5), 0x31: (6, 6), 0x32: (8, 5),
         0x33: (8, 6), 0x34: (8, 8), 0x35: (10, 5), 0x36: (10, 6), 0x37: (10, 8), 0x38: (10, 10),
         0x39: (12, 10), 0x3a: (12, 12)}
for _k, (_w, _h) in _ASTC.items():
    FMT[_k] = (16, _w, _h, (lambda bw, bh: lambda d, w, h: t2d.decode_astc(d, w, h, bw, bh))(_w, _h))
FMT.update({
    0x02: (1, 1, 1, None),   # R8
    0x09: (2, 1, 1, None),   # R8G8
})


def deswizzle(data, width_blocks, height_blocks, bpp, block_height_log2, switch2=False):
    """Tegra block-linear -> linear (em blocos)."""
    bh = 1 << block_height_log2
    gob_w_bytes = 64
    row_bytes = width_blocks * bpp
    width_gobs = (row_bytes + 63) // 64
    pad_h = ((height_blocks + 8 * bh - 1) // (8 * bh)) * (8 * bh)
    need = width_gobs * 512 * bh * (pad_h // (8 * bh))
    buf = np.frombuffer(data[:need].ljust(need, b'\0'), dtype=np.uint8)
    y = np.arange(height_blocks)[:, None]
    xb = (np.arange(width_blocks) * bpp)[None, :]
    gob = (y // (8 * bh)) * 512 * bh * width_gobs + (xb // 64) * 512 * bh + ((y % (8 * bh)) // 8) * 512
    if switch2:
        # Switch 2 (Ounc): ordem dos bits dentro do GOB achada por forca bruta (menor variacao total):
        # byte = x[0:4] | y0<<4 | y1<<5 | x4<<6 | y2<<7 | x5<<8
        addr = gob + (xb % 16) + (y % 2) * 16 + ((y >> 1) & 1) * 32 + ((xb >> 4) & 1) * 64             + ((y >> 2) & 1) * 128 + ((xb >> 5) & 1) * 256
    else:
        addr = gob + ((xb % 64) // 32) * 256 + ((y % 8) // 2) * 64 + ((xb % 32) // 16) * 32 + (y % 2) * 16 + (xb % 16)
    idx = addr[..., None] + np.arange(bpp)[None, None, :]
    return buf[idx].tobytes()


def textures(raw):
    assert raw[:4] == b'BNTX', raw[:4]
    nx = 0x20
    assert raw[nx:nx + 4] in (b'NX  ', b'Ounc'), raw[nx:nx + 4]  # Ounc = Switch 2
    count = struct.unpack_from('<I', raw, nx + 4)[0]
    info_arr = struct.unpack_from('<Q', raw, nx + 8)[0]
    out = []
    for i in range(count):
        bo = struct.unpack_from('<Q', raw, info_arr + 8 * i)[0]
        assert raw[bo:bo + 4] == b'BRTI', raw[bo:bo + 4]
        tile_mode = struct.unpack_from('<H', raw, bo + 0x12)[0]
        mips = struct.unpack_from('<H', raw, bo + 0x16)[0]
        fmt = struct.unpack_from('<I', raw, bo + 0x1C)[0]
        w, h, depth, arr = struct.unpack_from('<IIII', raw, bo + 0x24)
        layout = struct.unpack_from('<I', raw, bo + 0x34)[0]
        name_off, _, ptrs = struct.unpack_from('<QQQ', raw, bo + 0x60)
        nlen = struct.unpack_from('<H', raw, name_off)[0]
        name = raw[name_off + 2:name_off + 2 + nlen].decode()
        mip0 = struct.unpack_from('<Q', raw, ptrs)[0]
        out.append(dict(switch2=raw[nx:nx + 4] == b'Ounc', name=name, fmt=fmt, w=w, h=h, bhl=layout & 7, tile=tile_mode, mip0=mip0, mips=mips))
    return out


def decode(raw, index=0):
    t = textures(raw)[index]
    typ = t['fmt'] >> 8
    if typ not in FMT:
        raise ValueError('formato %x nao suportado (%s)' % (t['fmt'], t['name']))
    bpp, bw, bhh, dec = FMT[typ]
    wb, hb = (t['w'] + bw - 1) // bw, (t['h'] + bhh - 1) // bhh
    lin = deswizzle(raw[t['mip0']:], wb, hb, bpp, t['bhl'], t['switch2']) if t['tile'] == 0 else raw[t['mip0']:t['mip0'] + wb * hb * bpp]
    if dec is None:
        mode = {4: 'RGBA', 2: 'LA', 1: 'L'}[bpp]
        return Image.frombytes(mode, (wb, hb), lin).convert('RGBA'), t
    px = dec(lin, wb * bw, hb * bhh)  # BGRA
    im = Image.frombytes('RGBA', (wb * bw, hb * bhh), px, 'raw', 'BGRA')
    return im.crop((0, 0, t['w'], t['h'])), t
