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
import especiais as X

DATA = r'D:\OoT-Notas\data'

EXCLUIR_ITENS = {'Item_Dungeon_SmallKey', 'Item_Dungeon_BossKey', 'Item_Dungeon_Map', 'Item_Dungeon_Compass',
                 'Item_ScrubBusinessSeed', 'Obj_MiniGame_SmallKey'}
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
    return NOMES.get(i) or X.NOMES.get(i, i)


def nome_local(loc):
    if loc.get('tipo') in ('musica', 'npc'):
        return loc['nome']
    sala = f" sala {loc['sala']}" if loc.get('sala') is not None else ''
    return f"{AREAS.get(loc['area'], loc['area'])}{sala} #{str(loc['hash'])[-5:]}"


def carregar_locais():
    todos = json.load(open(os.path.join(DATA, 'rando_locais.json'), encoding='utf-8'))
    usar, fixos = [], []
    for l in todos:
        excl = (l['repetivel'] or l['area'] in EXCLUIR_AREAS or l['item'] in EXCLUIR_ITENS
                or l['gyaml'].startswith(('Obj_TBox_A_06', 'Obj_HrlCity_Shop')))
        (fixos if excl else usar).append(l)
    return usar + X.locais(), fixos   # (+ quem ensina musicas e os NPCs que dao itens: sempre na logica)


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


GRUPOS = {   # (o que o jogador escolhe embaralhar: --embaralhar, o menu do jogo; o resto fica com o item original)
    'masmorras': lambda l: not l.get('tipo') and l['area'] in G.MASMORRA_IDADE,
    'mundo': lambda l: not l.get('tipo') and l['area'] not in G.MASMORRA_IDADE,
    'npcs': lambda l: l.get('tipo') == 'npc',
    'musicas': lambda l: l.get('tipo') == 'musica',
    'lojas': lambda l: False,   # (as vitrines: especiais.embaralhar_lojas)
}


def gerar(seed, vanilla=False, tentativas=300, grupos=('masmorras', 'mundo')):
    """devolve (locais, fixos, colocados, tentativa, lojas): lojas = (vitrines, gyaml novo de cada uma) ou None"""
    locais, fixos = carregar_locais()
    entra = [any(GRUPOS[g](l) for g in grupos) for l in locais]
    base = {i: l['item'] for i, l in enumerate(locais) if not entra[i]}   # (fora da escolha: o item original, na logica)
    pool = [l['item'] for i, l in enumerate(locais) if entra[i]]
    rng = random.Random(hashlib.sha256(seed.encode()).digest())
    lojas = None
    G.ESCUDO_DEKU[0] = lambda s: True
    if 'lojas' in grupos and not vanilla:
        lojas = X.embaralhar_lojas(rng)
        G.ESCUDO_DEKU[0] = X.regra_escudo_deku(*lojas)
    if vanilla:
        colocados = {i: l['item'] for i, l in enumerate(locais)}
        return locais, fixos, colocados, 0, None
    prog = [x for x in pool if x in G.PROGRESSAO]
    resto = [x for x in pool if x not in G.PROGRESSAO]
    for tentativa in range(1, tentativas + 1):
        colocados = dict(base)
        a_colocar = prog[:]
        rng.shuffle(a_colocar)
        ok = True
        while a_colocar:
            item = a_colocar.pop()
            _, alc = alcance(locais, colocados, a_colocar)
            vazios = [i for i in alc if i not in colocados and X.pode(locais[i], item)]
            if not vazios:
                ok = False
                break
            colocados[rng.choice(vazios)] = item
        if not ok:
            continue
        # o resto: primeiro os locais com menos opcoes (os que pedem flag IsGet), depois os outros
        vazios = [i for i in range(len(locais)) if i not in colocados]
        r = resto[:]
        rng.shuffle(r)
        vazios.sort(key=lambda i: (sum(X.pode(locais[i], it) for it in set(r)), rng.random()))
        for i in vazios:
            k = next((k for k, it in enumerate(r) if X.pode(locais[i], it)), None)
            if k is None:
                ok = False
                break
            colocados[i] = r.pop(k)
        if not ok or r:
            continue
        # verificacao final
        sph, s, pegos = esferas(locais, colocados)
        if len(pegos) != len(locais) or 'ev:VITORIA' not in s.i:
            continue
        esfera_de = {colocados[i]: n for n, grupo in enumerate(sph) for i in grupo}
        if any(esfera_de.get(a, 99) >= esfera_de.get(b, -1) for a, b in G.ORDEM):
            continue
        return locais, fixos, colocados, tentativa, lojas
    raise RuntimeError('nao achei uma distribuicao valida em %d tentativas' % tentativas)


def spoiler(seed, locais, colocados, pasta, lojas=None):
    sph, s, _ = esferas(locais, colocados)
    linhas = [f'NS2-IA Randomizer - seed "{seed}"', f'gerado {time.strftime("%Y-%m-%d %H:%M")}', '',
              '== Caminho (esferas: o que da para pegar com o que ja se tem) ==']
    js = {'seed': seed, 'esferas': [], 'locais': {}}
    for n, grupo in enumerate(sph):
        prog = [i for i in grupo if colocados[i] in G.PROGRESSAO or colocados[i] in X.NOMES or colocados[i] == 'Item_Arrow_Ice']
        js['esferas'].append({nome_local(locais[i]): nome_item(colocados[i]) for i in grupo})
        if prog:
            linhas.append(f'Esfera {n}:')
            for i in prog:
                linhas.append(f'  {nome_local(locais[i]):45s} -> {nome_item(colocados[i])}')
    linhas += ['', '== Musicas e NPCs ==']
    for i, l in enumerate(locais):
        if l.get('tipo'):
            linhas.append(f'  {nome_local(l):45s} -> {nome_item(colocados[i]):20s} (original: {nome_item(l["item"])})')
            js['locais'][l['chave']] = {'local': nome_local(l), 'item': colocados[i], 'original': l['item']}
    if lojas:
        linhas += ['', '== Lojas ==']
        js['lojas'] = {}
        for v, novo in zip(lojas[0], lojas[1]):
            linhas.append(f'  {X.nome_vitrine(v):45s} -> {novo:28s} (original: {v["gyaml"]})')
            js['lojas'][X.nome_vitrine(v)] = {'item': novo, 'original': v['gyaml']}
        linhas += ['', '== Deku vendedores ==']
        for rel, h, k, orig, novo in lojas[2]:
            linhas.append(f'  {rel.split("/")[1]:20s} #{str(h)[-5:]} {k[-1]}  -> {novo:28s} (original: {orig})')
    linhas += ['', '== Todos os baus ==']
    for i, l in sorted(((i, l) for i, l in enumerate(locais) if not l.get('tipo')),
                       key=lambda x: (x[1]['area'], x[1].get('sala') or 0)):
        orig = nome_item(l['item'])
        linhas.append(f'  {nome_local(l):45s} -> {nome_item(colocados[i]):20s} (original: {orig})')
        js['locais'][str(l['hash'])] = {'local': nome_local(l), 'item': colocados[i], 'original': l['item']}
    os.makedirs(pasta, exist_ok=True)
    open(os.path.join(pasta, 'spoiler.txt'), 'w', encoding='utf-8').write('\n'.join(linhas) + '\n')
    json.dump(js, open(os.path.join(pasta, 'spoiler.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return len(sph)


def gravar_mod(locais, colocados, nome_mod='Randomizer', seed='', saida=None, rstb=None, grupos=None, lojas=None):
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
    cenas = {}   # (uma Cena por arquivo: baus e vitrines podem estar na mesma cena)

    def cena(rel):
        if rel not in cenas:
            cenas[rel] = M.Cena(rel)
        return cenas[rel]
    for rel, trocas in sorted(por_arquivo.items()):
        c = cena(rel)
        for h, item in trocas.items():
            c.trocar_drop(h, item)
    if lojas:
        n_vit = 0
        for rel, h, k, orig, novo in lojas[2]:
            if novo != orig:
                cena(rel).ator(h)[1]['Dynamic'][1][k] = (0xA0, novo)
        for v, novo in zip(lojas[0], lojas[1]):
            if novo != v['gyaml']:
                n_vit += 1
                for rel, h in v['copias']:
                    cena(rel).ator(h)[1]['Gyaml'] = (0xA0, novo)
        print(f'lojas: {n_vit} vitrines trocadas')
    for rel in sorted(cenas):
        c = cenas[rel]
        c.gravar(mod)
        tamanhos[c.rel] = c.tamanhos
    ed = X.edicoes_de_fluxo(locais, colocados)
    if ed:
        tamanhos.update(X.gravar_fluxos(ed, mod))
        print(f'fluxos de evento: {len(ed)} ({", ".join(sorted(ed))})')
    print(f'cutscenes: {M.liberar_cutscenes(mod)} liberadas para pular (abertura, creditos)')
    base = rstb or M.rstb_do_jogo()
    if base:
        subiu, sem = M.tabela_de_tamanhos(base, tamanhos, os.path.join(mod, 'rsizetable.zs'))
        print(f'rstb: {subiu} entradas aumentadas (base {base})' + (f'; sem entrada: {sem}' if sem else ''))
    else:
        print('rstb: AVISO sem tabela base: cenas maiores podem ser descartadas pelo jogo')
    open(os.path.join(mod, 'seed.txt'), 'w', encoding='utf-8').write(seed + '\n')
    if grupos:   # (o menu do jogo mostra o que esta seed embaralhou)
        open(os.path.join(mod, 'embaralhar.txt'), 'w', encoding='utf-8').write(','.join(grupos) + '\n')
    return mod, len(cenas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', default=None)
    ap.add_argument('--sem-mod', action='store_true')
    ap.add_argument('--vanilla', action='store_true', help='testa a logica com tudo no lugar original')
    ap.add_argument('--saida', help='pasta do Hookshot (romfs + rsizetable.zs + spoiler), em vez do mod do emulador')
    ap.add_argument('--rstb', help='a RSTB base (padrao: a do Hookshot, senao a do jogo)')
    ap.add_argument('--embaralhar', default='masmorras,mundo',
                    help='o que embaralhar, separado por virgula: ' + ', '.join(GRUPOS))
    a = ap.parse_args()
    grupos = [g for g in a.embaralhar.split(',') if g]
    ruins = [g for g in grupos if g not in GRUPOS]
    if ruins or not grupos:
        raise SystemExit(f'--embaralhar: escolha entre {", ".join(GRUPOS)} (veio {a.embaralhar!r})')
    seed = a.seed or time.strftime('%Y%m%d-%H%M%S')
    locais, fixos, colocados, tent, lojas = gerar(seed, vanilla=a.vanilla, grupos=grupos)
    if a.vanilla:
        sph, s, pegos = esferas(locais, colocados)
        print(f'vanilla: {len(pegos)}/{len(locais)} baus alcancaveis, vitoria={"ev:VITORIA" in s.i}, {len(sph)} esferas')
        for i, l in enumerate(locais):
            if i not in pegos:
                print('  inalcancavel:', nome_local(l), l['item'])
        return
    pasta = os.path.join(DATA, 'rando', seed)
    n = spoiler(seed, locais, colocados, pasta, lojas)
    nemb = sum(1 for l in locais if any(GRUPOS[g](l) for g in grupos))
    print(f'seed {seed} ({",".join(grupos)}): {nemb} locais embaralhados ({len(fixos) + len(locais) - nemb} fixos)'
          f'{", lojas" if lojas else ""}, tentativa {tent}, {n} esferas')
    print('spoiler:', os.path.join(pasta, 'spoiler.txt'))
    if not a.sem_mod:
        mod, narq = gravar_mod(locais, colocados, seed=seed, saida=a.saida, rstb=a.rstb, grupos=grupos, lojas=lojas)
        if a.saida:   # (o spoiler junto, para o jogador consultar se travar)
            import shutil
            for f in ('spoiler.txt', 'spoiler.json'):
                shutil.copy2(os.path.join(pasta, f), os.path.join(mod, f))
        print(f'mod: {mod} ({narq} arquivos de cena)')
        print('@@ok', seed)


if __name__ == '__main__':
    main()
