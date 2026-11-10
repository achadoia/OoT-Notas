"""Gera o pacote de dados do painel "Notas do Zelda" do NS2-IA a partir do RomFS local.

Saida (padrao D:\\NS2-IA\\notas\\0400486024DEC000\\):
  notas.json      areas, categorias, checks (com posicao no mapa e chave do save) e listas
  mapas\\*.jpg     mapas das areas (1000x720) tirados de UI/CustomTex/Map

uso: python gerar_notas.py [pasta_saida]
"""
import os, sys, json, re
import mmh3
sys.path.insert(0, os.path.dirname(__file__))
import ootlib as L
import bntx
from PIL import Image, ImageOps

GAME = r"D:/Ocarina of Time/jogos/The Legend of Zelda Ocarina of Time [0400486024dec000][v131072]"
OUT = sys.argv[1] if len(sys.argv) > 1 else r"D:\NS2-IA\notas\0400486024DEC000"
DATA = r"D:\OoT-Notas\data"
MAP_W, MAP_H = 1000, 720

AREA_PT = {
    'KokiriForest': 'Floresta Kokiri', 'KakarikoVillage': 'Vila Kakariko', 'LonLonRanch': 'Rancho Lon Lon',
    'Market': 'Mercado', 'GoronCity': 'Cidade Goron', 'ZoraDomain': 'Domínio Zora',
    'GerudoFortress': 'Fortaleza Gerudo', 'LostWood': 'Bosque Perdido', 'SacredForestMeadow': 'Prado Sagrado',
    'HyruleField': 'Campo de Hyrule', 'HyruleCastle': 'Castelo de Hyrule', 'Graveyard': 'Cemitério',
    'DeathMountainTrail': 'Trilha da Montanha da Morte', 'DeathMountainCrater': 'Cratera da Montanha da Morte',
    'ZoraRiver': 'Rio Zora', 'ZoraFountain': 'Fonte Zora', 'LakeHylia': 'Lago Hylia',
    'GerudoValley': 'Vale Gerudo', 'HountedWasteland': 'Deserto Assombrado', 'DesertColossus': 'Colosso do Deserto',
    'InsideTheDekuTree': 'Interior da Árvore Deku', 'DodongoCavern': 'Caverna dos Dodongos',
    'InsideJabuJabuBelly': 'Barriga do Jabu-Jabu', 'ForestTemple': 'Templo da Floresta',
    'FireTemple': 'Templo do Fogo', 'WaterTemple': 'Templo da Água', 'ShadowTemple': 'Templo das Sombras',
    'SpiritTemple': 'Templo do Espírito', 'BottomOfTheWell': 'Fundo do Poço', 'IceCavern': 'Caverna de Gelo',
    'GanonCastle': 'Castelo de Ganon', 'InsideGanonCastle': 'Interior do Castelo de Ganon',
    'GerudoTrainingGround': 'Campo de Treino Gerudo', 'DreamWorld': 'Mundo dos Sonhos',
}

# categoria: (nome, grupo, cor, letra, visivel por padrao[, rastreavel])
# rastreavel=False: o jogo NAO guarda no save (ResetType != 24, o objeto volta ao reentrar na area);
# aparece no mapa so como referencia, sem contador nem "pego".
CATS = {
    'skulltula': ('Skulltulas Douradas', 'Colecionáveis', '#f2c14e', 'S', True),
    'coracao': ('Pedaços de Coração', 'Colecionáveis', '#ff5d8f', '♥', True),
    'recipiente': ('Recipientes de Coração', 'Colecionáveis', '#e0245e', '♥', True),
    'bau_item': ('Baús com itens', 'Baús', '#3fb6ff', '★', True),
    'bau_chave': ('Baús de chaves, mapa e bússola', 'Baús', '#8fd14f', 'K', True),
    'bau_rupia': ('Baús de rupias e munição', 'Baús', '#9aa5b1', '$', True),
    'rupia_prata': ('Rupias Prateadas', 'Itens', '#d6dde6', '◆', False),
    'deku': ('Vendedores Deku', 'Referência', '#c58b4b', 'D', False, False),
    'parede': ('Paredes rachadas', 'Outros', '#b07cff', '✕', False),
}

DROP_PT = {
    'Item_Dungeon_SmallKey': 'Chave Pequena', 'Item_Dungeon_BossKey': 'Chave do Chefe', 'Item_Dungeon_Map': 'Mapa',
    'Item_Dungeon_Compass': 'Bússola', 'Obj_MiniGame_SmallKey': 'Chave (minigame)',
    'TBox_Rupee_Green': 'Rupia Verde', 'TBox_Rupee_Blue': 'Rupia Azul', 'TBox_Rupee_Red': 'Rupia Vermelha',
    'TBox_Rupee_Purple': 'Rupia Roxa', 'TBox_Rupee_Gold': 'Rupia Dourada', 'Obj_Heart_Piece': 'Pedaço de Coração',
    'Item_ScrubBusinessSeed': 'Semente Deku (troca)', 'TBox_Shield_Deku': 'Escudo Deku', 'TBox_Shield_Hylian': 'Escudo Hylian',
    'Item_Shield_Mirror': 'Escudo Espelhado', 'Item_BombBundle_Small': 'Bombas', 'Item_BombchuBundle_Small': 'Bombchus',
    'Item_Gauntlet_Silver': 'Manopla de Prata', 'Item_Gauntlet_Gold': 'Manopla de Ouro', 'TBox_ArrowBundle_Medium': 'Flechas',
    'TBox_ArrowBundle_Large': 'Flechas', 'TBox_DekuNutBundle': 'Nozes Deku', 'Item_Sword_Kokiri': 'Espada Kokiri',
    'Item_GlassTruth': 'Lente da Verdade', 'Item_BombBag_Small': 'Bolsa de Bombas', 'Item_Hammer': 'Martelo Megaton',
    'Item_Range_Bow': 'Arco das Fadas', 'Item_Arrow_Ice': 'Flecha de Gelo', 'Item_Hookshot': 'Gancho',
    'Item_HeavyBoot': 'Botas de Ferro', 'Item_Boomerang': 'Bumerangue', 'Item_DekuStickBundle_Small': 'Galhos Deku',
    'Item_Range_SlingShot': 'Estilingue', 'Tbox_MagicJar_Large': 'Pote de Magia', 'Item_HoverBoot': 'Botas Flutuantes',
    'Item_Longshot': 'Gancho Longo',
}
KEYISH = {'Item_Dungeon_SmallKey', 'Item_Dungeon_BossKey', 'Item_Dungeon_Map', 'Item_Dungeon_Compass', 'Obj_MiniGame_SmallKey'}

# listas sem mapa: flag nomeada -> (categoria da lista, nome)
LISTAS = [
    ('Canções', 'IsGet.Item_Melody_ZeldaLullaby', 'Canção de Ninar da Zelda'),
    ('Canções', 'IsGet.Item_Melody_EponaSong', 'Canção da Epona'),
    ('Canções', 'IsGet.Item_Melody_SariaSong', 'Canção da Saria'),
    ('Canções', 'IsGet.Item_Melody_SunSong', 'Canção do Sol'),
    ('Canções', 'IsGet.Item_Melody_TimeSong', 'Canção do Tempo'),
    ('Canções', 'IsGet.Item_Melody_StormSong', 'Canção das Tempestades'),
    ('Canções', 'IsGet.Item_Melody_ForestMinuet', 'Minueto da Floresta'),
    ('Canções', 'IsGet.Item_Melody_FireBolero', 'Bolero do Fogo'),
    ('Canções', 'IsGet.Item_Melody_WaterSerenade', 'Serenata da Água'),
    ('Canções', 'IsGet.Item_Melody_SpiritRequiem', 'Réquiem do Espírito'),
    ('Canções', 'IsGet.Item_Melody_ShadowNocturne', 'Noturno das Sombras'),
    ('Canções', 'IsGet.Item_Melody_LightPrelude', 'Prelúdio da Luz'),
]
ITEM_PT = {
    'Item_DekuStick': 'Galho Deku', 'Item_DekuNut': 'Noz Deku', 'Item_Bomb': 'Bombas', 'Weapon_Range_Bow': 'Arco das Fadas',
    'Item_Arrow_Fire': 'Flecha de Fogo', 'Item_Arrow_Ice': 'Flecha de Gelo', 'Item_Arrow_Light': 'Flecha de Luz',
    'Item_DinFire': 'Fogo de Din', 'Item_FaroreWind': 'Vento de Farore', 'Item_NayruLove': 'Amor de Nayru',
    'Weapon_Range_SlingShot': 'Estilingue', 'Item_Ocarina_Fairy': 'Ocarina das Fadas', 'Item_Ocarina_Time': 'Ocarina do Tempo',
    'Item_Bombchu': 'Bombchu', 'Item_Hookshot': 'Gancho', 'Item_Longshot': 'Gancho Longo', 'Item_Boomerang': 'Bumerangue',
    'Item_GlassTruth': 'Lente da Verdade', 'Item_MagicBean': 'Feijão Mágico', 'Item_Hammer': 'Martelo Megaton',
    'Item_Bottle': 'Garrafa', 'Item_WeirdEgg': 'Ovo Estranho', 'Item_Bottle_Letter': 'Carta do Ruto',
    'Weapon_Shield_Deku': 'Escudo Deku', 'Weapon_Shield_Hylian': 'Escudo Hylian', 'Weapon_Shield_Mirror': 'Escudo Espelhado',
    'Item_BombBag_Small': 'Bolsa de Bombas', 'Item_BulletBag_Small': 'Bolsa de Sementes', 'Item_Quiver_Small': 'Aljava',
    'Item_FairyBless_MP': 'Magia (Grande Fada)', 'Item_HeavyBoot': 'Botas de Ferro', 'Item_HoverBoot': 'Botas Flutuantes',
    'Item_Gauntlet_Silver': 'Manopla de Prata', 'Item_Gauntlet_Gold': 'Manopla de Ouro', 'Item_StoneOfAgony': 'Pedra da Agonia',
    'Weapon_Sword_Kokiri': 'Espada Kokiri', 'Weapon_Sword_Master': 'Espada Mestra', 'Weapon_Sword_Biggoron': 'Espada de Biggoron',
}


def cat_of(x):
    g, dyn = x['gyaml'], x.get('dyn') or {}
    if g == 'Enemy_Skulltula_Gold':
        return 'skulltula', 'Skulltula Dourada'
    if g == 'Obj_Heart_Piece':
        return 'coracao', 'Pedaço de Coração'
    if g == 'Obj_Heart_Container':
        return 'recipiente', 'Recipiente de Coração'
    if 'TBox' in g:
        drop = dyn.get('Drop__DropActor')
        nome = 'Baú: ' + DROP_PT.get(drop, drop or '?')
        if drop == 'Obj_Heart_Piece':
            return 'coracao', nome
        if drop in KEYISH:
            return 'bau_chave', nome
        if drop and (drop.startswith('Item_') and drop not in ('Item_BombBundle_Small', 'Item_BombchuBundle_Small', 'Item_DekuStickBundle_Small', 'Item_ScrubBusinessSeed')):
            return 'bau_item', nome
        return 'bau_rupia', nome
    if g == 'Obj_RupeeToken_Silver':
        return 'rupia_prata', 'Rupia Prateada'
    if g.startswith('Enemy_Scrub_Business'):
        return ('deku', 'Vendedor Deku') if not g.endswith('_Leaf') else (None, None)
    if g == 'WallCrack':
        return 'parede', 'Parede rachada'
    return None, None


def main():
    L.set_game(GAME)
    os.makedirs(os.path.join(OUT, 'mapas'), exist_ok=True)
    cap = L.byml(L.read('Game/MapCaptureInfo/MapCaptureInfo.game__MapCaptureInfo.bgyml'))['MapCaptureParamArray']
    menu = L.byml(L.read('Game/MapMenuInfo/MapMenuInfo.game__ui__MapMenuInfo.bgyml'))['MapMenuParamArray']
    areas, area_of_banc = [], {}
    for i, m in enumerate(menu):
        name = m['LocationName']
        c = cap[i]
        cam = c.get('CameraPos')
        if not cam:
            continue
        dungeon = bool(c.get('IsDungeon'))
        maps = {}
        for era, tex in zip(('crianca', 'adulto'), m['TextureName'][:2]):
            if not tex:
                continue
            if dungeon:
                rel = 'UI/CustomTex/Map/Dungeon/%s_All.bntx.zs' % tex
                if not L.find(rel):
                    rel = 'UI/CustomTex/Map/Dungeon/%s_State00_All.bntx.zs' % tex
            else:
                rel = 'UI/CustomTex/Map/Field/%s.bntx.zs' % tex
            if not L.find(rel):
                continue
            fn = os.path.basename(rel).replace('.bntx.zs', '.jpg')
            if not os.path.exists(os.path.join(OUT, 'mapas', fn)):
                im, _ = bntx.decode(L.read(rel))
                if dungeon:  # silhueta preta -> pergaminho
                    a = im.getchannel('A')
                    fill = Image.new('RGBA', im.size, (226, 196, 128, 255))
                    edge = Image.new('RGBA', im.size, (120, 70, 30, 255))
                    base = Image.new('RGBA', im.size, (23, 20, 28, 255))
                    base.paste(edge, (0, 0), a.point(lambda v: 255 if v > 20 else 0))
                    base.paste(fill, (0, 0), a.point(lambda v: 255 if v > 200 else 0))
                    im = base
                bg = Image.new('RGBA', im.size, (23, 20, 28, 255))
                bg.alpha_composite(im)
                bg.convert('RGB').resize((MAP_W, MAP_H), Image.LANCZOS).save(os.path.join(OUT, 'mapas', fn), quality=88)
            maps[era] = 'mapas/' + fn
        if not maps:
            continue
        areas.append(dict(id=name, nome=AREA_PT.get(name, name), masmorra=dungeon, mapas=maps,
                          cx=cam['X'], cz=cam['Z'], altura=c['Height']))
        for b in m['BancName'][:2]:
            area_of_banc.setdefault(b.split('_')[0], name)
    area_ids = {a['id'] for a in areas}
    bycam = {a['id']: a for a in areas}

    banc = json.load(open(os.path.join(DATA, 'banc_flags.json')))
    checks, seen = [], set()
    count = {}
    for x in banc:
        cat, nome = cat_of(x)
        if not cat or x['hash'] in seen:
            continue
        seen.add(x['hash'])
        parts = x['file'].split('/')
        folder, fname = parts[1], parts[2]
        era = 'adulto' if '_Adult' in fname else 'crianca' if '_Child' in fname else 'ambos'
        area = folder if folder in area_ids else area_of_banc.get(folder)
        a = bycam.get(area)
        X, Y, Z = x['pos'] if x.get('pos') else (0, 0, 0)
        px = py = None
        if a:
            s = MAP_H / a['altura']
            px, py = round(MAP_W / 2 + (X - a['cx']) * s, 1), round(MAP_H / 2 + (Z - a['cz']) * s, 1)
            if not (-50 < px < MAP_W + 50 and -50 < py < MAP_H + 50):
                px = py = None
        k = (area or folder, cat)
        count[k] = count.get(k, 0) + 1
        ck = dict(id='%016x' % x['hash'], cat=cat, nome=nome, area=area or folder,
                  area_nome=AREA_PT.get(area or folder, folder), era=era, x=px, y=py,
                  n=count[k], chave='%016x' % x['hash'])
        if 'TBox' in x['gyaml']:
            # bau aberto = Bool "IsTreasureBoxOpen.<hash do ator em decimal>" (achado 2026-11-09 abrindo
            # o bau do pedaco de coracao no Vale Gerudo); a chave de 64 bits do bau nunca liga
            ck['flag'] = mmh3.hash('IsTreasureBoxOpen.%d' % x['hash'], 0, signed=False)
            del ck['chave']
        checks.append(ck)
    for c in checks:
        c['nome'] = '%s #%d' % (c['nome'], c['n']) if c['cat'] in ('skulltula', 'coracao', 'recipiente', 'rupia_prata', 'deku', 'parede') else c['nome']
        del c['n']

    listas = [dict(lista=l, nome=n, flag=mmh3.hash(f, 0, signed=False), flag_nome=f) for l, f, n in LISTAS]
    names = json.load(open(os.path.join(DATA, 'names.json')))
    for h, n in sorted(names.items(), key=lambda kv: kv[1]):
        m = re.match(r'IsGet\.((?:Item|Weapon)_[A-Za-z_]+)$', n)
        if m and 'Melody' not in n and m.group(1) in ITEM_PT:
            listas.append(dict(lista='Itens', nome=ITEM_PT[m.group(1)], flag=int(h), flag_nome=n))

    cats = [dict(id=k, nome=v[0], grupo=v[1], cor=v[2], letra=v[3], visivel=v[4],
                 rastreavel=v[5] if len(v) > 5 else True) for k, v in CATS.items()]
    # banc (cena) atual -> [area, era]. O save guarda String64 "Sequence_CurrentBanc" (ex. "Market_Child"),
    # Bool "Sequence_IsChildhood" e Vector3 "Player_Pos_For_Map"; o jogo faz autosave a cada troca de area.
    bancs = {}
    for m in menu:
        area_id = m['LocationName']
        if area_id not in area_ids:
            continue
        nomes = m['BancName'][:2] + [c.get('BancName') for c in m.get('ChangeBancInfo', []) if c.get('BancName')]
        for i, b in enumerate(nomes):
            era = 'adulto' if (i == 1 or '_Adult' in b) and '_Child' not in b else 'crianca'
            if m['BancName'][0] == m['BancName'][1]:
                era = ''  # masmorra: a idade vem de Sequence_IsChildhood
            bancs.setdefault(b, [area_id, era])
    if 'GanonCastle' in area_ids:
        bancs.setdefault('InsideGanonCastle', ['GanonCastle', ''])
    estado = {k: mmh3.hash(k, 0, signed=False) for k in
              ('Sequence_CurrentBanc', 'Sequence_IsChildhood', 'Player_Pos_For_Map', 'Player_Rot_For_Map')}
    out = dict(versao=2, jogo='The Legend of Zelda: Ocarina of Time', titulo='0400486024DEC000',
               mapa_w=MAP_W, mapa_h=MAP_H, areas=areas, categorias=cats, checks=checks, listas=listas,
               bancs=bancs, estado=estado)
    json.dump(out, open(os.path.join(OUT, 'notas.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    from collections import Counter
    print(len(areas), 'areas', len(checks), 'checks', len(listas), 'itens de lista')
    print(Counter(c['cat'] for c in checks))
    print('sem posicao no mapa:', sum(1 for c in checks if c['x'] is None))


if __name__ == '__main__':
    main()
