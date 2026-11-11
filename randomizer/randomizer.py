"""Randomizer do OoT Remake (NS2-IA) - baus.

uso:  python randomizer.py [--seed TEXTO] [--sem-mod] [--vanilla]
  gera data/rando/<seed>/spoiler.{json,txt} e o mod LayeredFS 'Randomizer' do NS2-IA.

Algoritmo (mesmo desenho do SoH, codigo proprio):
  1. locais = baus fora das exclusoes; pool = itens desses baus
  2. progressao por AssumedFill: para cada item, supoe que o jogador ja tem todos os itens
     ainda nao colocados, calcula o que e alcancavel e sorteia um bau vazio alcancavel
  3. resto (uteis e lixo) aleatorio
  4. verificacao: busca por esferas -> todos os baus alcancaveis + vitoria + ordem dos progressivos
"""
import os, sys, json, random, hashlib, argparse, time
sys.path.insert(0, os.path.dirname(__file__))
import logica as G

DATA = r'D:\OoT-Notas\data'

EXCLUIR_ITENS = {'Item_Dungeon_SmallKey', 'Item_Dungeon_BossKey', 'Item_Dungeon_Map', 'Item_Dungeon_Compass',
                 'Item_ScrubBusinessSeed', 'Obj_MiniGame_SmallKey',
                 # a Espada Kokiri fica no bau dela (Floresta Kokiri, aberto desde o inicio): sem espada equipada o Remake
                 # nao deixa usar a bomba (o Link levanta e guarda), visto na seed 20261111-121010
                 'Item_Sword_Kokiri'}
EXCLUIR_AREAS = {'DreamWorld'}

NOMES = {
    'Item_Sword_Kokiri': 'Espada Kokiri', 'Item_Range_SlingShot': 'Estilingue', 'Item_Boomerang': 'Bumerangue',
    'Item_BombBag_Small': 'Bolsa de Bombas', 'Item_Range_Bow': 'Arco', 'Item_Hookshot': 'Gancho',
    'Item_Longshot': 'Gancho Longo', 'Item_Hammer': 'Martelo Megaton', 'Item_HoverBoot': 'Botas de Pouso',
    'Item_HeavyBoot': 'Botas de Ferro', 'Item_Gauntlet_Silver': 'Manopla de Prata',
    'Item_Gauntlet_Gold': 'Manopla de Ouro', 'Item_GlassTruth': 'Lente da Verdade',
    'Item_Shield_Mirror': 'Escudo Espelhado', 'Item_Arrow_Ice': 'Flecha de Gelo',
    'Obj_Heart_Piece': 'Peça de Coração', 'Item_BombBundle_Small': 'Bombas (5)',
    'Item_BombchuBundle_Small': 'Bombchus (5)', 'Item_DekuStickBundle_Small': 'Galhos Deku',
    'TBox_DekuNutBundle': 'Nozes Deku', 'TBox_ArrowBundle_Medium': 'Flechas (10)',
    'TBox_ArrowBundle_Large': 'Flechas (30)', 'Tbox_MagicJar_Large': 'Jarro de Magia',
    'TBox_Rupee_Green': 'Rupia Verde', 'TBox_Rupee_Blue': 'Rupia Azul', 'TBox_Rupee_Red': 'Rupia Vermelha',
    'TBox_Rupee_Purple': 'Rupia Roxa', 'TBox_Rupee_Gold': 'Rupia de Ouro',
}
AREAS = {
    'InsideTheDekuTree': 'Árvore Deku', 'DodongoCavern': 'Caverna dos Dodongos',
    'InsideJabuJabuBelly': 'Barriga do Jabu-Jabu', 'BottomOfTheWell': 'Fundo do Poço',
    'ForestTemple': 'Templo da Floresta', 'FireTemple': 'Templo do Fogo', 'WaterTemple': 'Templo da Água',
    'ShadowTemple': 'Templo das Sombras', 'SpiritTemple': 'Templo do Espírito', 'IceCavern': 'Caverna de Gelo',
    'GerudoTrainingGround': 'Campo de Treino Gerudo', 'InsideGanonCastle': 'Castelo de Ganon',
    'KokiriForest': 'Floresta Kokiri', 'LostWood': 'Bosque Perdido', 'SacredForestMeadow': 'Prado Sagrado',
    'HyruleField': 'Campo de Hyrule', 'KakarikoVillage': 'Kakariko', 'Graveyard': 'Cemitério',
    'DeathMountainTrail': 'Trilha da Montanha da Morte', 'DeathMountainCrater': 'Cratera da Montanha',
    'GoronCity': 'Cidade Goron', 'ZoraRiver': 'Rio Zora', 'ZoraDomain': 'Domínio Zora',
    'ZoraFountain': 'Fonte Zora', 'GerudoValley': 'Vale Gerudo', 'GerudoFortress': 'Fortaleza Gerudo',
    'HountedWasteland': 'Deserto Assombrado', 'DesertColossus': 'Colosso do Deserto', 'Market': 'Mercado',
}


def nome_item(i):
    return NOMES.get(i, i)


def nome_local(loc):
    sala = f" sala {loc['sala']}" if loc.get('sala') is not None else ''
    return f"{AREAS.get(loc['area'], loc['area'])}{sala} #{str(loc['hash'])[-5:]}"


def carregar_locais():
    todos = json.load(open(os.path.join(DATA, 'rando_locais.json'), encoding='utf-8'))
    usar, fixos = [], []
    for l in todos:
        excl = (l['repetivel'] or l['area'] in EXCLUIR_AREAS or l['item'] in EXCLUIR_ITENS
                or l['gyaml'].startswith(('Obj_TBox_A_06', 'Obj_HrlCity_Shop')))
        (fixos if excl else usar).append(l)
    return usar, fixos


def alcance(locais, colocados, assumidos):
    """Ponto fixo: eventos + itens dos baus alcancaveis. Devolve (estado, baus alcancaveis)."""
    s = G.Estado(assumidos)
    alc = set()
    mudou = True
    while mudou:
        mudou = False
        for ev, regra in G.EVENTOS.items():
            if ev not in s.i and regra(s):
                s.i.add(ev); mudou = True
        for idx, loc in enumerate(locais):
            if idx in alc or not G.acessivel(loc, s):
                continue
            alc.add(idx); mudou = True
            if idx in colocados:
                s.i.add(colocados[idx])
            ev = G.EVENTO_DO_BAU.get(loc.get('evento'))
            if ev:
                s.i.add(ev)
    return s, alc


def esferas(locais, colocados):
    """Playthrough: em cada esfera, os itens pegos so valem na proxima."""
    s = G.Estado([])
    pegos = set()
    out = []
    while True:
        mudou = True
        while mudou:  # eventos valem na hora
            mudou = False
            for ev, regra in G.EVENTOS.items():
                if ev not in s.i and regra(s):
                    s.i.add(ev); mudou = True
        novos = [i for i, loc in enumerate(locais) if i not in pegos and G.acessivel(loc, s)]
        if not novos:
            break
        out.append(novos)
        for i in novos:
            pegos.add(i)
            if i in colocados:
                s.i.add(colocados[i])
            ev = G.EVENTO_DO_BAU.get(locais[i].get('evento'))
            if ev:
                s.i.add(ev)
    return out, s, pegos


def gerar(seed, vanilla=False, tentativas=50):
    locais, fixos = carregar_locais()
    pool = [l['item'] for l in locais]
    if vanilla:
        colocados = {i: l['item'] for i, l in enumerate(locais)}
        return locais, fixos, colocados, 0
    rng = random.Random(hashlib.sha256(seed.encode()).digest())
    prog = [x for x in pool if x in G.PROGRESSAO]
    resto = [x for x in pool if x not in G.PROGRESSAO]
    for tentativa in range(1, tentativas + 1):
        colocados = {}
        a_colocar = prog[:]
        rng.shuffle(a_colocar)
        ok = True
        while a_colocar:
            item = a_colocar.pop()
            _, alc = alcance(locais, colocados, a_colocar)
            vazios = [i for i in alc if i not in colocados]
            if not vazios:
                ok = False
                break
            colocados[rng.choice(vazios)] = item
        if not ok:
            continue
        vazios = [i for i in range(len(locais)) if i not in colocados]
        r = resto[:]
        rng.shuffle(r)
        for i, item in zip(vazios, r):
            colocados[i] = item
        # verificacao final
        sph, s, pegos = esferas(locais, colocados)
        if len(pegos) != len(locais) or 'ev:VITORIA' not in s.i:
            continue
        esfera_de = {colocados[i]: n for n, grupo in enumerate(sph) for i in grupo}
        if any(esfera_de.get(a, 99) >= esfera_de.get(b, -1) for a, b in G.ORDEM):
            continue
        return locais, fixos, colocados, tentativa
    raise RuntimeError('nao achei uma distribuicao valida em %d tentativas' % tentativas)


def spoiler(seed, locais, colocados, pasta):
    sph, s, _ = esferas(locais, colocados)
    linhas = [f'NS2-IA Randomizer - seed "{seed}"', f'gerado {time.strftime("%Y-%m-%d %H:%M")}', '',
              '== Caminho (esferas: o que da para pegar com o que ja se tem) ==']
    js = {'seed': seed, 'esferas': [], 'locais': {}}
    for n, grupo in enumerate(sph):
        prog = [i for i in grupo if colocados[i] in G.PROGRESSAO or colocados[i] == 'Item_Arrow_Ice']
        js['esferas'].append({nome_local(locais[i]): nome_item(colocados[i]) for i in grupo})
        if prog:
            linhas.append(f'Esfera {n}:')
            for i in prog:
                linhas.append(f'  {nome_local(locais[i]):45s} -> {nome_item(colocados[i])}')
    linhas += ['', '== Todos os baus ==']
    for i, l in sorted(enumerate(locais), key=lambda x: (x[1]['area'], x[1].get('sala') or 0)):
        orig = nome_item(l['item'])
        linhas.append(f'  {nome_local(l):45s} -> {nome_item(colocados[i]):20s} (original: {orig})')
        js['locais'][str(l['hash'])] = {'local': nome_local(l), 'item': colocados[i], 'original': l['item']}
    os.makedirs(pasta, exist_ok=True)
    open(os.path.join(pasta, 'spoiler.txt'), 'w', encoding='utf-8').write('\n'.join(linhas) + '\n')
    json.dump(js, open(os.path.join(pasta, 'spoiler.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return len(sph)


def gravar_mod(locais, colocados, nome_mod='Randomizer', seed='', saida=None, rstb=None):
    """saida: a pasta do Hookshot (D:\\hookshot\\zelda\\randomizer.novo): saida\\romfs + saida\\rsizetable.zs; sem ela, o mod
    LayeredFS do emulador (pausado)"""
    import modfs as M
    por_arquivo = {}
    for i, l in enumerate(locais):
        if colocados[i] != l['item']:
            for rel in l['arquivos']:
                por_arquivo.setdefault(rel, {})[l['hash']] = colocados[i]
    if saida:
        if os.path.isdir(saida):
            import shutil
            shutil.rmtree(saida)
        os.makedirs(saida)
        mod = saida
    else:
        mod = M.limpar_mod(nome_mod)
    tamanhos = {}
    for rel, trocas in sorted(por_arquivo.items()):
        c = M.Cena(rel)
        for h, item in trocas.items():
            c.trocar_drop(h, item)
        c.gravar(mod)
        tamanhos[c.rel] = c.tamanhos
    print(f'cutscenes: {M.liberar_cutscenes(mod)} liberadas para pular (abertura, creditos)')
    base = rstb or M.rstb_do_jogo()
    if base:
        subiu, sem = M.tabela_de_tamanhos(base, tamanhos, os.path.join(mod, 'rsizetable.zs'))
        print(f'rstb: {subiu} entradas aumentadas (base {base})' + (f'; sem entrada: {sem}' if sem else ''))
    else:
        print('rstb: AVISO sem tabela base: cenas maiores podem ser descartadas pelo jogo')
    open(os.path.join(mod, 'seed.txt'), 'w', encoding='utf-8').write(seed + '\n')
    return mod, len(por_arquivo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', default=None)
    ap.add_argument('--sem-mod', action='store_true')
    ap.add_argument('--vanilla', action='store_true', help='testa a logica com tudo no lugar original')
    ap.add_argument('--saida', help='pasta do Hookshot (romfs + rsizetable.zs + spoiler), em vez do mod do emulador')
    ap.add_argument('--rstb', help='a RSTB base (padrao: a do Hookshot, senao a do jogo)')
    a = ap.parse_args()
    seed = a.seed or time.strftime('%Y%m%d-%H%M%S')
    locais, fixos, colocados, tent = gerar(seed, vanilla=a.vanilla)
    if a.vanilla:
        sph, s, pegos = esferas(locais, colocados)
        print(f'vanilla: {len(pegos)}/{len(locais)} baus alcancaveis, vitoria={"ev:VITORIA" in s.i}, {len(sph)} esferas')
        for i, l in enumerate(locais):
            if i not in pegos:
                print('  inalcancavel:', nome_local(l), l['item'])
        return
    pasta = os.path.join(DATA, 'rando', seed)
    n = spoiler(seed, locais, colocados, pasta)
    print(f'seed {seed}: {len(locais)} baus embaralhados ({len(fixos)} fixos), tentativa {tent}, {n} esferas')
    print('spoiler:', os.path.join(pasta, 'spoiler.txt'))
    if not a.sem_mod:
        mod, narq = gravar_mod(locais, colocados, seed=seed, saida=a.saida, rstb=a.rstb)
        if a.saida:   # (o spoiler junto, para o jogador consultar se travar)
            import shutil
            for f in ('spoiler.txt', 'spoiler.json'):
                shutil.copy2(os.path.join(pasta, f), os.path.join(mod, f))
        print(f'mod: {mod} ({narq} arquivos de cena)')
        print('@@ok', seed)


if __name__ == '__main__':
    main()
