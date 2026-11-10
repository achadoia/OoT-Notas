"""Grava cenas (Banc) modificadas como mod LayeredFS do NS2-IA."""
import os, sys, shutil, zstandard
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
sys.path.insert(0, os.path.dirname(__file__))
import ootlib as L
import bymlrw as B

GAME = r"D:/Ocarina of Time/jogos/The Legend of Zelda Ocarina of Time [0400486024dec000][v131072]"
L.set_game(GAME)
TITLE = '0400486024DEC000'
LOAD = os.path.expandvars(r'%APPDATA%\eden\load\\' + TITLE)


def dict_do_arquivo(raw):
    """O dicionario zstd que abre esse arquivo (para recomprimir igual)."""
    for name, d in L._load_dicts().items():
        try:
            zstandard.ZstdDecompressor(dict_data=d).decompress(raw, max_output_size=1 << 30)
            return d
        except zstandard.ZstdError:
            continue
    return None


class Cena:
    def __init__(self, rel):
        self.rel = rel.replace('\\', '/')
        self.raw = open(L.find(self.rel), 'rb').read()
        self.root, self.ver, self.E = B.load(L.unzs(self.raw))
        self.mudou = False

    def atores(self):
        t, lst = self.root[1]['Actors']
        return lst

    def hash_de(self, a):
        t, v = a[1]['Hash']
        return int.from_bytes(v, 'little' if self.E == '<' else 'big') if t in (0xD4, 0xD5) else v

    def ator(self, hash_):
        for a in self.atores():
            if self.hash_de(a) == hash_:
                return a
        raise KeyError(hash_)

    def trocar_drop(self, hash_, item):
        a = self.ator(hash_)
        dyn = a[1]['Dynamic'][1]
        antes = dyn['Drop__DropActor'][1]
        dyn['Drop__DropActor'] = (0xA0, item)
        # o bau pode trocar o item se o jogador ja tem o CheckActor: tira para nao interferir
        for k in ('Drop__CheckActor', 'Drop__DropActor_Substitute'):
            dyn.pop(k, None)
        self.mudou = True
        return antes

    def gravar(self, mod_dir):
        dados = B.dump(self.root, self.ver, self.E)
        d = dict_do_arquivo(self.raw)
        comp = zstandard.ZstdCompressor(level=16, dict_data=d) if d else zstandard.ZstdCompressor(level=16)
        dest = os.path.join(mod_dir, 'romfs', *self.rel.split('/'))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(comp.compress(dados))
        assert B.plain(B.load(L.unzs(open(dest, 'rb').read()))[0]) == B.plain(self.root)
        return dest


def limpar_mod(nome):
    p = os.path.join(LOAD, nome)
    if os.path.isdir(p):
        shutil.rmtree(p)
    return p
