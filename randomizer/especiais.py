"""Locais especiais do randomizer: quem ensina as musicas, NPCs que dao itens, e as vitrines das lojas.

Como o Remake entrega essas coisas (lido dos fluxos de evento, Event/EventFlow/*.bfevfl, evfl.py):
- musicas: Dm_SY_Ocarina tem uma acao PouchSystemActor.EventTriggerAddOrRemovePouchContent por musica (Actor =
  Item_Melody_X); o professor so escolhe qual roda (MelodyType). Trocar o Actor dessas acoes = trocar a musica que cada
  professor da (a licao continua tocando a musica original).
- NPCs: chamam o subfluxo Dm_SY_GetInEvent passando o item em ActorName (que vira o modelo, a fanfarra, a janela e o
  item no inventario). Trocar esse ActorName = trocar o item.
- "ja entreguei?": a maioria usa flags proprias (HavePlayedEvent.*, <Npc>_IsGetHeartPiece...), que nao mudam. As que
  usam IsGet.<item original> (fadas, Sheik da cratera, o moinho) sao reescritas para IsGet.<item novo>; por isso esses
  locais so recebem itens que TEM flag IsGet (ISGET).
- lojas: cada vitrine e um ator Shop_<item> na cena (o ator ja tem o item e o preco); embaralhar = trocar o Gyaml
  entre as vitrines (mascaras, que sao emprestimo, ficam de fora).
"""
import json
import os
import random

import logica as G

DATA = r'D:\OoT-Notas\data'

# (chave da regra em logica.REGRAS, tipo, nome, item original, o fluxo que entrega)
MUSICAS = [
    ('musica_impa', G.ZL, 'Impa (Castelo de Hyrule)'),
    ('musica_malon', G.EPONA, 'Malon (Fazenda Lon Lon)'),
    ('musica_saria', G.SARIA, 'Saria (Prado Sagrado)'),
    ('musica_tumba', G.SOL, 'Tumba Real (Cemitério)'),
    ('musica_tempo', G.TEMPO, 'Zelda (fosso do Castelo)'),
    ('musica_moinho', G.TEMPEST, 'Moinho (Kakariko)'),
    ('musica_minueto', G.MINUETO, 'Sheik (Prado Sagrado)'),
    ('musica_bolero', G.BOLERO, 'Sheik (Cratera)'),
    ('musica_serenata', G.SERENATA, 'Sheik (Caverna de Gelo)'),
    ('musica_requiem', G.REQUIEM, 'Sheik (Colosso do Deserto)'),
    ('musica_noturno', G.NOTURNO, 'Sheik (Kakariko)'),
    ('musica_preludio', G.PRELUDIO, 'Sheik (Templo do Tempo)'),
]
NPCS = [   # (chave, item original, nome, fluxo)
    ('fada_din', 'Item_DinFire', 'Grande Fada de Din (Castelo)', 'Dm_FairyFountain_Din'),
    ('fada_farore', 'Item_FaroreWind', 'Grande Fada de Farore (Fonte Zora)', 'Dm_FairyFountain_Frore'),
    ('fada_nayru', 'Item_NayruLove', 'Grande Fada de Nayru (Colosso)', 'Dm_FairyFountain_Nayru'),
    ('fada_poder', 'Item_FairyBless_MP', 'Grande Fada do Poder (Montanha)', 'Dm_FairyFountain_Power'),
    ('fada_sabedoria', 'Item_FairyBless_MPDouble', 'Grande Fada da Sabedoria (Castelo de Ganon)', 'Dm_FairyFountain_Wisdom'),
    ('fada_coragem', 'Item_FairyBless_DefenseDouble', 'Grande Fada da Coragem (Cratera)', 'Dm_FairyFountain_Courage'),
    ('darunia', 'Item_Gauntlet_Goron', 'Darunia (Cidade Goron)', 'Dm_Goron_0030'),
    ('cartao_gerudo', 'Item_Token_Gerudo', 'Cartão Gerudo (Fortaleza)', 'Dm_Gerudo_0025'),
    ('coracao_telhado', 'Obj_Heart_Piece', 'Homem do telhado (Kakariko)', 'Npc_Hylia_001_Adult'),
    ('coracao_skullkid', 'Obj_Heart_Piece', 'Skull Kid (Bosque Perdido)', 'Npc_SkullKid_Child'),
    ('coracao_sapos', 'Obj_Heart_Piece', 'Sapos (Rio Zora)', 'MiniGame_FrogTenors'),
    ('coracao_dampe', 'Obj_Heart_Piece', 'Dampé (Cemitério)', 'Npc_Hylia_Dampe_001'),
]
FADAS = [n for n in NPCS if n[0].startswith('fada_')]
# fluxos que perguntam IsGet.<musica do local> para saber se o local ja foi feito; (critico: sem reescrever, o local
# pode nunca dar o item novo)
GUARDAS_MUSICA = {
    'Dm_MelodyGet_Fire': ([G.BOLERO], True),
    'Npc_Hylia_009_Adult': ([G.TEMPEST], True),
    'Npc_Hylia_051_Adult': ([G.TEMPEST], True),
    'Npc_Hylia_Sheik_Adult': ([G.MINUETO], True),
    'SageOfWater': ([G.BOLERO, G.MINUETO, G.REQUIEM], False),
    'Npc_Kokiri_Fado_Child': ([G.SARIA], False),
}
# o ator dado -> a flag IsGet que o jogo liga (so existem 43; ver data/strings.txt)
ISGET = {
    'Item_Hookshot': 'IsGet.Item_Hookshot', 'Item_Longshot': 'IsGet.Item_Longshot',
    'Item_Range_Bow': 'IsGet.Weapon_Range_Bow', 'Item_Range_SlingShot': 'IsGet.Weapon_Range_SlingShot',
    'Item_Sword_Kokiri': 'IsGet.Weapon_Sword_Kokiri', 'Item_HoverBoot': 'IsGet.Armor_Adult_HoverBoot',
    'Item_GlassTruth': 'IsGet.Armor_GlassTruth', 'Item_Arrow_Ice': 'IsGet.Item_Arrow_Ice',
    'Item_BombBag_Small': 'IsGet.Item_BombBag_Small', 'TBox_Shield_Deku': 'IsGet.Weapon_Shield_Deku',
}
for _i in ('Item_DinFire', 'Item_FaroreWind', 'Item_NayruLove', 'Item_FairyBless_MP', 'Item_FairyBless_MPDouble',
           'Item_FairyBless_DefenseDouble', 'Item_Token_Gerudo', G.ZL, G.SARIA, G.SOL, G.TEMPEST, G.MINUETO, G.BOLERO,
           G.SERENATA, G.REQUIEM, G.NOTURNO):
    ISGET[_i] = 'IsGet.' + _i
LOCAIS_COM_ISGET = {k for k, *_ in FADAS} | {'musica_moinho', 'musica_bolero', 'musica_minueto'}
SO_NPC = {'Item_FairyBless_MP', 'Item_FairyBless_MPDouble', 'Item_FairyBless_DefenseDouble'}   # (nao vao para bau)
NOMES = {
    G.ZL: 'Cantiga de Zelda', G.EPONA: 'Canção de Epona', G.SARIA: 'Canção de Saria', G.SOL: 'Canção do Sol',
    G.TEMPO: 'Canção do Tempo', G.TEMPEST: 'Canção da Tempestade', G.MINUETO: 'Minueto da Floresta',
    G.BOLERO: 'Bolero do Fogo', G.SERENATA: 'Serenata da Água', G.REQUIEM: 'Réquiem do Espírito',
    G.NOTURNO: 'Noturno da Sombra', G.PRELUDIO: 'Prelúdio da Luz',
    'Item_DinFire': 'Fogo de Din', 'Item_FaroreWind': 'Vento de Farore', 'Item_NayruLove': 'Amor de Nayru',
    'Item_FairyBless_MP': 'Magia', 'Item_FairyBless_MPDouble': 'Magia dupla',
    'Item_FairyBless_DefenseDouble': 'Defesa dupla', 'Item_Gauntlet_Goron': 'Bracelete Goron',
    'Item_Token_Gerudo': 'Cartão Gerudo',
}


def locais():
    """os locais especiais no formato dos baus (randomizer.py): sempre na lista; fora da escolha ficam com o original"""
    out = []
    for chave, item, nome in MUSICAS:
        out.append({'hash': chave, 'tipo': 'musica', 'chave': chave, 'item': item, 'nome': nome, 'area': 'musica',
                    'gyaml': '', 'idades': ['Ambas'], 'arquivos': []})
    for chave, item, nome, fluxo in NPCS:
        out.append({'hash': chave, 'tipo': 'npc', 'chave': chave, 'item': item, 'nome': nome, 'area': 'npc',
                    'gyaml': '', 'idades': ['Ambas'], 'arquivos': [], 'fluxo': fluxo})
    return out


def pode(loc, item):
    """restricoes de tipo (como as listas de locais do SoH): musicas so nos locais de musica; IsGet nos guardados"""
    musica_loc = loc.get('tipo') == 'musica'
    if musica_loc != (item in G.MUSICAS):
        return False
    if loc.get('chave') in LOCAIS_COM_ISGET and item not in ISGET:
        return False
    if item in SO_NPC and loc.get('tipo') != 'npc':
        return False
    return True


# ---- o que gravar: fluxos de evento ----
def edicoes_de_fluxo(locs, colocados):
    """{fluxo: [(mapa de strings, eventos alvo (None = todos), filtro de subfluxo)]} a partir do que foi colocado"""
    ed = {}
    por_chave = {l.get('chave'): (l, colocados[i]) for i, l in enumerate(locs) if l.get('tipo') in ('musica', 'npc')}
    # musicas: as acoes do Dm_SY_Ocarina
    m = {l['item']: novo for l, novo in por_chave.values() if l['tipo'] == 'musica' and novo != l['item']}
    if m:
        ed.setdefault('Dm_SY_Ocarina', []).append(('pouch', m))
    # as guardas IsGet.<musica do local>
    musica_do_local = {l['item']: novo for l, novo in por_chave.values() if l['tipo'] == 'musica'}
    for fluxo, (musicas, critico) in GUARDAS_MUSICA.items():
        g = {}
        for orig in musicas:
            novo = musica_do_local.get(orig, orig)
            if novo == orig:
                continue
            if novo in ISGET:
                g['IsGet.' + orig] = ISGET[novo]
            elif critico:
                raise AssertionError(f'{fluxo}: {novo} sem flag IsGet')
        if g:
            ed.setdefault(fluxo, []).append(('todas', g))
    # NPCs: o ActorName do Dm_SY_GetInEvent
    for l, novo in por_chave.values():
        if l['tipo'] == 'npc' and novo != l['item']:
            ed.setdefault(l['fluxo'], []).append(('getin', {l['item']: novo}))
    # as fadas: IsGet.<item original de cada fada> -> IsGet.<o que essa fada da agora>, nos 6 fluxos das fadas
    g = {}
    for chave, orig, _, _ in FADAS:
        l, novo = por_chave[chave]
        if novo != orig:
            g['IsGet.' + orig] = ISGET[novo]
    if g:
        for _, _, _, fluxo in FADAS:
            ed.setdefault(fluxo, []).append(('todas', g))
    return ed


def gravar_fluxos(ed, mod_dir):
    """grava os fluxos editados em mod_dir\\romfs; devolve {caminho romfs: (tamanho antes, depois)} para a RSTB"""
    import ootlib as L
    import modfs as M
    import evfl
    import zstandard
    tamanhos = {}
    for fluxo, ops in sorted(ed.items()):
        rel = f'Event/EventFlow/{fluxo}.bfevfl.zs'
        raw = open(L.find(rel), 'rb').read()
        d = L.unzs(raw)
        e = evfl.Editor(d)
        for tipo, mapa in ops:
            if tipo == 'pouch':
                alvo = {ev['i'] for ev in e.e.events if ev['tipo'] == 0
                        and ev['acao'] == 'EventTriggerAddOrRemovePouchContent'}
            elif tipo == 'getin':
                alvo = {ev['i'] for ev, fl, _, _ in evfl.subflows(e.e) if fl == 'Dm_SY_GetInEvent'}
            else:
                alvo = None
            n = e.trocar_strings(mapa, alvo)
            if not n:
                raise AssertionError(f'{fluxo}: nada trocado para {mapa}')
        novo = e.bytes()
        dic = M.dict_do_arquivo(raw)
        comp = zstandard.ZstdCompressor(level=16, dict_data=dic) if dic else zstandard.ZstdCompressor(level=16)
        dest = os.path.join(mod_dir, 'romfs', *rel.split('/'))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, 'wb').write(comp.compress(novo))
        evfl.Evfl(L.unzs(open(dest, 'rb').read()))   # (relê: tem que abrir)
        tamanhos[rel] = (len(d), len(novo))
    return tamanhos


# ---- lojas ----
def vitrines():
    """as vitrines por (area, indice, gyaml original) -> todas as copias (arquivo, hash) e as idades"""
    lst = json.load(open(os.path.join(DATA, 'rando_lojas.json'), encoding='utf-8'))
    out = {}
    for v in lst:
        if v['gyaml'].startswith('Shop_Mask_'):
            continue
        k = (v['area'], v['indice'], v['gyaml'])
        w = out.setdefault(k, {'area': v['area'], 'indice': v['indice'], 'gyaml': v['gyaml'], 'copias': [],
                               'idades': set()})
        w['copias'] += [(rel, v['hash']) for rel in v['arquivos']]
        w['idades'] |= set(v['idades'])
    return [out[k] for k in sorted(out)]


def embaralhar_lojas(rng):
    vs = vitrines()
    itens = [v['gyaml'] for v in vs]
    while True:   # (o Escudo Deku tem que ficar onde a crianca compra: sem ele nao se entra na Arvore Deku)
        rng.shuffle(itens)
        k = itens.index('Shop_Weapon_Shield_Deku')
        if 'Child' in vs[k]['idades'] and vs[k]['area'] in ('KokiriForest', 'Market'):
            return vs, itens


def regra_escudo_deku(vs, itens):
    """o Escudo Deku a venda: onde caiu (crianca); os baus com escudo tambem valem (TBox_Shield_Deku)"""
    acesso = {'KokiriForest': lambda s: True, 'Market': lambda s: True, 'ZoraDomain': lambda s: s.tem(G.ZL),
              'GoronCity': lambda s: s.forca(1) or s.tem(G.BOMBS), 'KakarikoVillage': lambda s: True}
    regras = [acesso.get(v['area'], lambda s: False) for v, it in zip(vs, itens)
              if it == 'Shop_Weapon_Shield_Deku' and ('Child' in v['idades'] or 'Ambas' in v['idades'])]
    return lambda s: s.tem('TBox_Shield_Deku') or any(r(s) for r in regras)


def nome_vitrine(v):
    areas = {'KokiriForest': 'Loja Kokiri', 'Market': 'Mercado', 'KakarikoVillage': 'Kakariko', 'GoronCity': 'Loja Goron',
             'ZoraDomain': 'Loja Zora'}
    return f"{areas.get(v['area'], v['area'])} #{v['indice']}"
