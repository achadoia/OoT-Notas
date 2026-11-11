"""Leitura do BFEVFL (fluxos de evento) do OoT Remake: mesmo desenho do evfl do BotW (versao 4), so o que o randomizer precisa.
Os ponteiros sao offsets de 64 bits no arquivo; as strings ficam no pool (u16 tamanho + texto + 0)."""
import struct

TIPOS = {0: "arg", 1: "container", 2: "int", 3: "bool", 4: "float", 5: "string", 6: "wstring",
         7: "int[]", 8: "bool[]", 9: "float[]", 10: "string[]", 11: "wstring[]", 12: "actor"}


class Evfl:
    def __init__(self, d):
        self.d = d
        assert d[:6] == b"BFEVFL", d[:8]
        self.n_flows = struct.unpack_from("<H", d, 0x20)[0]
        fptr = self.q(self.q(0x28))
        self.flow = fptr
        na, nac, nq, ne, nep = struct.unpack_from("<5H", d, fptr + 0x10)
        self.nome = self.s(self.q(fptr + 0x20))
        actors_p, events_p = self.q(fptr + 0x28), self.q(fptr + 0x30)
        self.actors = []
        for i in range(na):
            a = actors_p + i * 0x38
            n_act, n_q = struct.unpack_from("<HH", d, a + 0x30)
            acts = [self.s(self.q(self.q(a + 0x18) + k * 8)) for k in range(n_act)]
            qs = [self.s(self.q(self.q(a + 0x20) + k * 8)) for k in range(n_q)]
            self.actors.append({"nome": self.s(self.q(a)), "sub": self.s(self.q(a + 8)), "acoes": acts, "consultas": qs})
        self.events = []
        for i in range(ne):
            e = events_p + i * 0x30
            ev = {"i": i, "off": e, "nome": self.s(self.q(e)), "tipo": d[e + 8]}
            if ev["tipo"] == 0:
                nxt, ai, aci = struct.unpack_from("<HHH", d, e + 0xA)
                ev.update(next=nxt, ator=self.actors[ai]["nome"], acao=self.actors[ai]["acoes"][aci], params_ptr_off=e + 0x10,
                          params=self.container(self.q(e + 0x10)))
            elif ev["tipo"] == 1:
                n, ai, qi = struct.unpack_from("<HHH", d, e + 0xA)
                ev.update(ncasos=n, ator=self.actors[ai]["nome"], consulta=self.actors[ai]["consultas"][qi],
                          params=self.container(self.q(e + 0x10)))
            self.events.append(ev)

    def q(self, o):
        return struct.unpack_from("<Q", self.d, o)[0]

    def s(self, o):
        if not o:
            return None
        n = struct.unpack_from("<H", self.d, o)[0]
        return self.d[o + 2:o + 2 + n].decode("utf-8", "replace")

    def dic(self, o):
        n = struct.unpack_from("<I", self.d, o + 4)[0]
        return [self.s(self.q(o + 8 + 16 * (k + 1) + 8)) for k in range(n)]

    def container(self, o):
        """{chave: (tipo, valor, offset_do_ponteiro_da_string ou None)}"""
        if not o:
            return {}
        t, n = self.d[o], struct.unpack_from("<H", self.d, o + 2)[0]
        assert t == 1, t
        chaves = self.dic(self.q(o + 8))
        out = {}
        for k in range(n):
            it = self.q(o + 0x10 + k * 8)
            tt, cnt = self.d[it], struct.unpack_from("<H", self.d, it + 2)[0]
            v, po = None, None
            if tt == 1:
                v = self.container(it)
            elif tt in (5, 0):
                po = it + 0x10
                v = self.s(self.q(po))
            elif tt == 2:
                v = struct.unpack_from("<i", self.d, it + 0x10)[0]
            elif tt == 3:
                v = struct.unpack_from("<I", self.d, it + 0x10)[0] != 0
            elif tt == 4:
                v = struct.unpack_from("<f", self.d, it + 0x10)[0]
            elif tt == 12:
                v = (self.s(self.q(it + 0x10)), self.s(self.q(it + 0x18)))
            else:
                v = "<%s x%d>" % (TIPOS.get(tt, tt), cnt)
            out[chaves[k]] = (TIPOS.get(tt, tt), v, po)
        return out


def subflows(e):
    """as chamadas de subfluxo: (evento, fluxo, entrada, params)"""
    for ev in e.events:
        if ev["tipo"] == 4:
            o = ev["off"]
            yield ev, e.s(e.q(o + 0x18)), e.s(e.q(o + 0x20)), e.container(e.q(o + 0x10))


def entradas(e):
    """{nome da entrada: indice do primeiro evento}"""
    fp = e.flow
    nep = struct.unpack_from("<H", e.d, fp + 0x18)[0]
    nomes = e.dic(e.q(fp + 0x38))
    eps = e.q(fp + 0x40)
    out = {}
    for k in range(nep):
        out[nomes[k]] = struct.unpack_from("<H", e.d, eps + k * 0x20 + 0x1A)[0] if False else eps + k * 0x20
    return out


class Editor:
    """Troca strings de parametros sem mexer no resto: a string nova vai no fim do arquivo (u16 tamanho + texto + 0) e
    so o ponteiro (que ja esta na tabela de relocacao) muda. O tamanho do arquivo no cabecalho (0x1C) acompanha."""

    def __init__(self, d):
        self.d = bytearray(d)
        self.e = Evfl(bytes(d))
        self.novas = {}

    def _string(self, s):
        if s not in self.novas:
            while len(self.d) % 8:
                self.d.append(0)
            self.novas[s] = len(self.d)
            b = s.encode("utf-8")
            self.d += struct.pack("<H", len(b)) + b + b"\0"
        return self.novas[s]

    def apontar(self, ptr_off, s):
        struct.pack_into("<Q", self.d, ptr_off, self._string(s))

    def trocar_strings(self, mapa, so_eventos=None):
        """troca o valor de todo parametro string (de acao, switch ou subfluxo, em qualquer profundidade) que seja uma
        chave de mapa; so_eventos: limita a esses indices. Devolve quantas trocas."""
        n = 0

        def andar(c):
            nonlocal n
            for k, (t, v, po) in c.items():
                if t == "container":
                    andar(v)
                elif t == "string" and po and v in mapa and mapa[v] != v:
                    self.apontar(po, mapa[v])
                    n += 1
        for ev in self.e.events:
            if so_eventos is not None and ev["i"] not in so_eventos:
                continue
            if ev["tipo"] in (0, 1):
                andar(ev["params"])
            elif ev["tipo"] == 4:
                andar(self.e.container(self.e.q(ev["off"] + 0x10)))
        return n

    def bytes(self):
        while len(self.d) % 8:
            self.d.append(0)
        struct.pack_into("<I", self.d, 0x1C, len(self.d))
        return bytes(self.d)
