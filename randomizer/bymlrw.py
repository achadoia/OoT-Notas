"""BYML v7 (OoT Remake / TotK) sem perda: le para nos tipados e grava de volta.

No tipado = (tipo, valor):
  0xA0 str, 0xA1 binario, 0xD0 bool, 0xD1 int32, 0xD2 float, 0xD3 uint32,
  0xD4 int64, 0xD5 uint64, 0xD6 double, 0xFF null,
  0xC0 lista[no], 0xC1 dict{str: no}, 0x20/0x21 dict-hash{int: no}
"""
import struct

CONTAINERS = (0xC0, 0xC1, 0x20, 0x21)


class Reader:
    def __init__(self, d):
        self.d = d
        assert d[:2] in (b'YB', b'BY')
        self.E = '<' if d[:2] == b'YB' else '>'
        self.order = 'little' if self.E == '<' else 'big'
        self.ver, kt, st, root = struct.unpack_from(self.E + 'HIII', d, 2)
        self.keys = self._strtab(kt) if kt else []
        self.strs = self._strtab(st) if st else []
        self.root = self._node(d[root], root) if root else None

    def _u24(self, o):
        return int.from_bytes(self.d[o:o + 3], self.order)

    def _u32(self, o):
        return struct.unpack_from(self.E + 'I', self.d, o)[0]

    def _strtab(self, off):
        d = self.d
        assert d[off] == 0xC2
        n = self._u24(off + 1)
        offs = struct.unpack_from(self.E + '%dI' % (n + 1), d, off + 4)
        return [d[off + offs[i]:d.index(b'\0', off + offs[i])].decode('utf-8') for i in range(n)]

    def _val(self, t, raw):
        d, E = self.d, self.E
        if t == 0xA0: return (t, self.strs[raw])
        if t == 0xA1:
            n = self._u32(raw)
            return (t, bytes(d[raw + 4:raw + 4 + n]))
        if t in (0xD0, 0xD1, 0xD2, 0xD3):
            return (t, raw)  # bits crus de 32 bits: grava igual
        if t in (0xD4, 0xD5, 0xD6):
            return (t, d[raw:raw + 8])
        if t == 0xFF: return (t, raw)
        if t in CONTAINERS: return self._node(t, raw)
        raise ValueError('tipo %02x' % t)

    def _node(self, t, off):
        d = self.d
        assert d[off] == t
        n = self._u24(off + 1)
        if t == 0xC0:
            types = d[off + 4:off + 4 + n]
            vo = off + 4 + ((n + 3) & ~3)
            return (t, [self._val(types[i], self._u32(vo + 4 * i)) for i in range(n)])
        if t == 0xC1:
            out = {}
            for i in range(n):
                e = off + 4 + 8 * i
                out[self.keys[self._u24(e)]] = self._val(d[e + 3], self._u32(e + 4))
            return (t, out)
        hs = 4 if t == 0x20 else 8
        es = hs + 4
        types = d[off + 4 + es * n: off + 4 + es * n + n]
        out = {}
        for i in range(n):
            e = off + 4 + es * i
            out[int.from_bytes(d[e:e + hs], self.order)] = self._val(types[i], self._u32(e + hs))
        return (t, out)


def load(data):
    r = Reader(data)
    return r.root, r.ver, r.E


def _collect(node, keys, strs):
    t, v = node
    if t == 0xA0:
        strs.add(v)
    elif t == 0xC0:
        for x in v: _collect(x, keys, strs)
    elif t == 0xC1:
        for k, x in v.items():
            keys.add(k); _collect(x, keys, strs)
    elif t in (0x20, 0x21):
        for x in v.values(): _collect(x, keys, strs)


def dump(root, ver=7, E='<'):
    order = 'little' if E == '<' else 'big'
    keys, strs = set(), set()
    _collect(root, keys, strs)
    keys = sorted(keys, key=lambda s: s.encode('utf-8'))
    strs = sorted(strs, key=lambda s: s.encode('utf-8'))
    kidx = {k: i for i, k in enumerate(keys)}
    sidx = {s: i for i, s in enumerate(strs)}
    out = bytearray(16)

    def align4():
        while len(out) % 4: out.append(0)

    def strtab(lst):
        align4()
        start = len(out)
        n = len(lst)
        out.extend(b'\xC2' + n.to_bytes(3, order))
        table_pos = len(out)
        out.extend(b'\0' * 4 * (n + 1))
        offs = []
        for s in lst:
            offs.append(len(out) - start)
            out.extend(s.encode('utf-8') + b'\0')
        offs.append(len(out) - start)
        struct.pack_into(E + '%dI' % (n + 1), out, table_pos, *offs)
        return start

    kt = strtab(keys) if keys else 0
    st = strtab(strs) if strs else 0
    align4()

    def inline(node):
        """valor de 32 bits de um filho; containers/64 bits sao gravados depois e corrigidos."""
        t, v = node
        if t == 0xA0: return sidx[v]
        if t in (0xD0, 0xD1, 0xD2, 0xD3, 0xFF): return v
        return None

    def write(node):
        t, v = node
        align4()
        pos = len(out)
        if t == 0xA1:
            out.extend(struct.pack(E + 'I', len(v)) + v)
            return pos
        if t in (0xD4, 0xD5, 0xD6):
            out.extend(v)
            return pos
        items = list(v.items()) if t != 0xC0 else list(enumerate(v))
        n = len(items)
        out.extend(bytes([t]) + n.to_bytes(3, order))
        slots = []
        if t == 0xC0:
            out.extend(bytes(x[0] for _, x in items))
            align4()
            for _, x in items:
                slots.append((len(out), x)); out.extend(b'\0\0\0\0')
        elif t == 0xC1:
            for k, x in sorted(items, key=lambda kv: kidx[kv[0]]):
                out.extend(kidx[k].to_bytes(3, order) + bytes([x[0]]))
                slots.append((len(out), x)); out.extend(b'\0\0\0\0')
        else:
            hs = 4 if t == 0x20 else 8
            items.sort(key=lambda kv: kv[0])
            for h, x in items:
                out.extend(h.to_bytes(hs, order))
                slots.append((len(out), x)); out.extend(b'\0\0\0\0')
            out.extend(bytes(x[0] for _, x in items))
            align4()
        for slot, x in slots:
            val = inline(x)
            if val is None:
                val = write(x)
            struct.pack_into(E + 'I', out, slot, val)
        return pos

    root_off = write(root) if root is not None else 0
    out[0:2] = b'YB' if E == '<' else b'BY'
    struct.pack_into(E + 'HIII', out, 2, ver, kt, st, root_off)
    return bytes(out)


def plain(node):
    """no tipado -> valores Python (para comparar/inspecionar)."""
    t, v = node
    if t == 0xC0: return [plain(x) for x in v]
    if t in (0xC1, 0x20, 0x21): return {k: plain(x) for k, x in v.items()}
    return (t, v)
