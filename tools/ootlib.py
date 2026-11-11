"""Leitura dos formatos do OoT Remake (mesma engine do TotK): .zs (zstd + ZsDic), SARC, BYML, progress.sav."""
import os, struct, zstandard

ROMFS_DIRS = []  # update primeiro, base depois


def set_game(root):
    ROMFS_DIRS.clear()
    # OOT_ROMFS=<pasta romfs solta> (ex.: D:\hookshot\romfs, a versao nativa de PC) tem prioridade; tambem e o que se
    # usa quando o dump base/updates nao existe mais
    solta = os.environ.get('OOT_ROMFS') or ''
    if not solta and not os.path.isdir(os.path.join(root, 'base')) and os.path.isdir(r'D:\hookshot\romfs'):
        solta = r'D:\hookshot\romfs'
    if solta and os.path.isdir(solta):
        ROMFS_DIRS.append(solta)
        return
    upd = os.path.join(root, 'updates')
    if os.path.isdir(upd):
        for v in sorted(os.listdir(upd), key=lambda s: -int(s) if s.isdigit() else 0):
            p = os.path.join(upd, v, 'romfs')
            if os.path.isdir(p):
                ROMFS_DIRS.append(p)
    ROMFS_DIRS.append(os.path.join(root, 'base', 'romfs'))


def find(rel):
    for d in ROMFS_DIRS:
        p = os.path.join(d, rel)
        if os.path.exists(p):
            return p
    return None


# ---------------- SARC ----------------
def sarc(data):
    assert data[:4] == b'SARC', data[:4]
    hl, bom = struct.unpack_from('<HH', data, 4)
    data_off = struct.unpack_from('<I', data, 0xC)[0]
    p = hl
    assert data[p:p + 4] == b'SFAT'
    _, n, _ = struct.unpack_from('<HHI', data, p + 4)
    nodes = []
    for i in range(n):
        h, attr, s, e = struct.unpack_from('<IIII', data, p + 12 + 16 * i)
        nodes.append((attr, s, e))
    q = p + 12 + 16 * n
    assert data[q:q + 4] == b'SFNT'
    names_off = q + 8
    out = {}
    for attr, s, e in nodes:
        no = (attr & 0xFFFF) * 4
        z = data.index(b'\0', names_off + no)
        name = data[names_off + no:z].decode('utf-8')
        out[name] = data[data_off + s:data_off + e]
    return out


# ---------------- zstd ----------------
_dicts = None


def _load_dicts():
    global _dicts
    if _dicts is not None:
        return _dicts
    raw = open(find('Pack/ZsDic.pack.zs'), 'rb').read()
    pack = sarc(zstandard.ZstdDecompressor().decompress(raw, max_output_size=1 << 28))
    _dicts = {}
    for name, d in pack.items():
        zd = zstandard.ZstdCompressionDict(d)
        _dicts[name] = zd
    return _dicts


def unzs(raw):
    # dict id está no frame header; deixa a lib escolher testando os dicts
    if raw[:4] != b'\x28\xb5\x2f\xfd':
        return raw
    try:
        return zstandard.ZstdDecompressor().decompress(raw, max_output_size=1 << 30)
    except zstandard.ZstdError:
        pass
    for name, d in _load_dicts().items():
        try:
            return zstandard.ZstdDecompressor(dict_data=d).decompress(raw, max_output_size=1 << 30)
        except zstandard.ZstdError:
            continue
    raise ValueError('nenhum dicionario zstd serviu')


def read(rel):
    p = find(rel)
    if p is None:
        raise FileNotFoundError(rel)
    return unzs(open(p, 'rb').read())


# ---------------- BYML ----------------
class Byml:
    def __init__(self, d):
        self.d = d
        assert d[:2] in (b'YB', b'BY'), d[:2]
        self.E = '<' if d[:2] == b'YB' else '>'
        self.ver, kt, st, root = struct.unpack_from(self.E + 'HIII', d, 2)
        self.keys = self._strtab(kt) if kt else []
        self.strs = self._strtab(st) if st else []
        self.root = self.node(d[root], root) if root else None

    def u24(self, o):
        return int.from_bytes(self.d[o:o + 3], 'little' if self.E == '<' else 'big')

    def u32(self, o):
        return struct.unpack_from(self.E + 'I', self.d, o)[0]

    def _strtab(self, off):
        d = self.d
        assert d[off] == 0xC2
        n = self.u24(off + 1)
        offs = struct.unpack_from(self.E + '%dI' % (n + 1), d, off + 4)
        return [d[off + offs[i]:d.index(b'\0', off + offs[i])].decode('utf-8', 'replace') for i in range(n)]

    def val(self, t, raw):
        d, E = self.d, self.E
        if t == 0xA0: return self.strs[raw]
        if t == 0xD0: return bool(raw)
        if t == 0xD1: return struct.unpack('<i', struct.pack('<I', raw))[0]
        if t == 0xD2: return struct.unpack('<f', struct.pack('<I', raw))[0]
        if t == 0xD3: return raw
        if t == 0xD4: return struct.unpack_from(E + 'q', d, raw)[0]
        if t == 0xD5: return struct.unpack_from(E + 'Q', d, raw)[0]
        if t == 0xD6: return struct.unpack_from(E + 'd', d, raw)[0]
        if t == 0xFF: return None
        if t == 0xA1:
            n = self.u32(raw)
            return bytes(d[raw + 4:raw + 4 + n])
        if t in (0xC0, 0xC1, 0x20, 0x21): return self.node(t, raw)
        return ('?%02x' % t, raw)

    def node(self, t, off):
        d = self.d
        assert d[off] == t, (hex(t), hex(d[off]), off)
        n = self.u24(off + 1)
        if t == 0xC0:
            types = d[off + 4:off + 4 + n]
            vo = off + 4 + ((n + 3) & ~3)
            return [self.val(types[i], self.u32(vo + 4 * i)) for i in range(n)]
        if t == 0xC1:
            out = {}
            for i in range(n):
                e = off + 4 + 8 * i
                if self.E == '<':
                    k = self.u24(e); ty = d[e + 3]
                else:
                    k = self.u24(e); ty = d[e + 3]
                out[self.keys[k]] = self.val(ty, self.u32(e + 4))
            return out
        if t in (0x20, 0x21):
            hs = 4 if t == 0x20 else 8
            es = hs + 4
            types = d[off + 4 + es * n: off + 4 + es * n + n]
            out = {}
            for i in range(n):
                e = off + 4 + es * i
                h = int.from_bytes(d[e:e + hs], 'little' if self.E == '<' else 'big')
                out[h] = self.val(types[i], self.u32(e + hs))
            return out
        raise ValueError('node %x' % t)


def byml(data):
    return Byml(data).root


# ---------------- progress.sav ----------------
# id da secao no progress.sav (marcador hash 0, valor = id) -> tipo do GameDataList.
# Conferido 2026-11-09 contando entradas com SaveFileIndex 0 no GameDataList.Product.110.
SECTION_TYPES = {0: 'Bool', 1: 'BoolArray', 2: 'Int', 3: 'IntArray', 4: 'Float', 5: 'FloatArray',
                 6: 'Enum', 7: 'EnumArray', 8: 'Vector2', 9: 'Vector2Array', 10: 'Vector3',
                 11: 'Vector3Array', 12: 'String16', 13: 'String16Array', 14: 'String32',
                 15: 'String32Array', 16: 'String64', 17: 'String64Array', 18: 'Binary',
                 19: 'BinaryArray', 20: 'UInt', 21: 'UIntArray', 22: 'Int64', 23: 'Int64Array',
                 24: 'UInt64', 25: 'UInt64Array', 26: 'WString16', 27: 'WString16Array',
                 28: 'WString32', 29: 'WString32Array', 30: 'WString64', 31: 'WString64Array',
                 32: 'Bool64bitKey'}


def read_save(path):
    """Devolve (secoes, keys64, bruto).
    secoes = {tipo: {hash32: valor_u32}} (bool/int direto; arrays/strings = offset no arquivo).
    keys64 = set de chaves Bool64bitKey LIGADAS (atores das fases ja pegos/quebrados/abertos);
    a secao 32 tem 1 entrada cujo valor e o offset de uma lista de u64 ate o fim do arquivo (0 = fim)."""
    d = open(path, 'rb').read()
    magic, ver, end = struct.unpack_from('<III', d, 0)
    assert magic == 0x01020304
    out = {}
    cur = out.setdefault('Bool', {})
    off = 0x28
    while off < end:
        h, v = struct.unpack_from('<II', d, off)
        off += 8
        if h == 0:
            cur = out.setdefault(SECTION_TYPES.get(v, 'T%d' % v), {})
            continue
        cur[h] = v
    keys = set()
    for h, o in out.get('Bool64bitKey', {}).items():
        while o + 8 <= len(d):
            k = struct.unpack_from('<Q', d, o)[0]
            o += 8
            if k == 0:
                break
            keys.add(k)
    return out, keys, d
