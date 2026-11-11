"""Grava cenas (Banc) modificadas como mod LayeredFS do NS2-IA."""
import os, sys, shutil, struct, zstandard
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
        self.tamanhos = (len(L.unzs(self.raw)), len(dados))   # (descomprimidos: original, novo) para a RSTB
        return dest


CUTSCENES_TRAVADAS = [   # (as unicas com SkipSetting/DisableSkip; o titulo Dm_Title_0005 fica como esta)
    'Event/EventSetting/EventSettingComponentList/Dm_Kokiri_0000.engine__event__EventSettingComponentList.bgyml',   # abertura
    'Event/EventSetting/EventSettingComponentList/Dm_StaffCredit_0005.engine__event__EventSettingComponentList.bgyml',  # creditos
]


def liberar_cutscenes(mod_dir):
    """Tira a trava de pular (SkipSetting -> DisableSkip) da abertura e dos creditos: as outras cutscenes ja aceitam o pular
    do proprio jogo. O arquivo fica menor (a RSTB nao precisa mudar). Devolve quantos foram gravados."""
    n = 0
    for rel in CUTSCENES_TRAVADAS:
        p = L.find(rel)
        if not p:
            print('cutscenes: AVISO nao achei', rel)
            continue
        root, ver, E = B.load(open(p, 'rb').read())
        comps = root[1]['Components'][1]
        if comps.pop('SkipSetting', None) is None:
            continue
        dest = os.path.join(mod_dir, 'romfs', *rel.split('/'))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(B.dump(root, ver, E))
        assert 'SkipSetting' not in B.plain(B.load(open(dest, 'rb').read())[0])['Components']
        n += 1
    return n


def tabela_de_tamanhos(base_zs, tamanhos, destino):
    """A RSTB (System/Resource/ResourceSizeTable.*.rsizetable.zs: "RESTBL", u32 versao, u32 tamanho do nome, u32 entradas
    por hash, u32 entradas por nome; por hash: u32 CRC-32 do caminho sem .zs, u32 tamanho) com as entradas das cenas
    reescritas aumentadas: o motor DESCARTA um arquivo maior que a sua entrada (foi a tela preta do v1 no NS2-IA: as cenas
    do bymlrw saem 10-20% maiores). tamanhos: {caminho romfs com .zs: (tamanho original, tamanho novo)}, descomprimidos.
    Grava destino (zstd sem dicionario, que o jogo aceita) e devolve (entradas aumentadas, caminhos sem entrada)."""
    import zlib
    b = bytearray(L.unzs(open(base_zs, 'rb').read()))
    if b[:6] != b'RESTBL':
        raise SystemExit(f'{base_zs} nao e uma RESTBL')
    nome_len, n_hash, n_nome = struct.unpack_from('<III', b, 10)
    quer = {}
    for rel, (antes, depois) in tamanhos.items():
        if depois > antes:
            chave = rel[:-3] if rel.endswith('.zs') else rel
            quer[zlib.crc32(chave.encode())] = (chave, depois - antes)
    subiu = 0
    for i in range(n_hash):
        at = 22 + 8 * i
        h, tam = struct.unpack_from('<II', b, at)
        if h in quer:   # (o que cresceu + 4 KB de folga; a entrada ja tem a folga do motor sobre o original)
            struct.pack_into('<I', b, at + 4, tam + quer.pop(h)[1] + 0x1000)
            subiu += 1
    base_nomes = 22 + 8 * n_hash
    for i in range(n_nome):
        at = base_nomes + (nome_len + 4) * i
        nome = bytes(b[at:at + nome_len]).split(b'\0')[0].decode('utf-8', 'replace')
        h = zlib.crc32(nome.encode())
        if h in quer and quer[h][0] == nome:
            tam, = struct.unpack_from('<I', b, at + nome_len)
            struct.pack_into('<I', b, at + nome_len, tam + quer.pop(h)[1] + 0x1000)
            subiu += 1
    os.makedirs(os.path.dirname(destino) or '.', exist_ok=True)
    with open(destino, 'wb') as f:
        f.write(zstandard.ZstdCompressor(level=16).compress(bytes(b)))
    return subiu, [v[0] for v in quer.values()]


def rstb_do_jogo():
    """a RSTB a usar de base: a do Hookshot (prompts\\rsizetable.zs: a do jogo com a fonte dos botoes aumentada), senao a
    do proprio jogo"""
    hs = r'D:\hookshot\prompts\rsizetable.zs'
    if os.path.isfile(hs):
        return hs
    for d in L.ROMFS_DIRS:
        pasta = os.path.join(d, 'System', 'Resource')
        if os.path.isdir(pasta):
            for n in sorted(os.listdir(pasta)):
                if n.startswith('ResourceSizeTable.') and n.endswith('.rsizetable.zs'):
                    return os.path.join(pasta, n)
    return None


def limpar_mod(nome):
    p = os.path.join(LOAD, nome)
    if os.path.isdir(p):
        shutil.rmtree(p)
    return p
