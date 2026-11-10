"""Logica do randomizer (glitchless, conservadora) para o OoT Remake.

Ideia (inspirada no SoH, codigo proprio): cada bau pertence a uma area; a area tem uma regra
de acesso por idade. Em masmorras a regra e CONSERVADORA: qualquer bau exige tudo o que o
jogo original exige para terminar a masmorra (entrada + itens usados la dentro). Assim o
gerador nunca pressupoe um caminho que talvez nao exista no layout do Remake.

Recompensas de NPC/historia (musicas, ocarina, garrafa, magia, tunicas, pedras, medalhoes)
continuam no lugar original e entram como EVENTOS.
"""

# ---- itens que o randomizer embaralha e que a logica usa ----
KOKIRI = 'Item_Sword_Kokiri'
SLING = 'Item_Range_SlingShot'
BOOM = 'Item_Boomerang'
BOMBS = 'Item_BombBag_Small'
BOW = 'Item_Range_Bow'
HOOK = 'Item_Hookshot'
LONG = 'Item_Longshot'
HAMMER = 'Item_Hammer'
HOVER = 'Item_HoverBoot'
IRON = 'Item_HeavyBoot'
SILVER = 'Item_Gauntlet_Silver'
GOLD = 'Item_Gauntlet_Gold'
LENS = 'Item_GlassTruth'
MIRROR = 'Item_Shield_Mirror'

PROGRESSAO = [KOKIRI, SLING, BOOM, BOMBS, BOW, HOOK, LONG, HAMMER, HOVER, IRON, SILVER, GOLD, LENS, MIRROR]
# progressivos: o segundo so pode aparecer depois do primeiro (o Remake talvez nao faca upgrade)
ORDEM = [(HOOK, LONG), (SILVER, GOLD)]

# ---- areas de masmorra -> idade em que se entra ----
MASMORRA_IDADE = {
    'InsideTheDekuTree': 'Child', 'DodongoCavern': 'Child', 'InsideJabuJabuBelly': 'Child',
    'BottomOfTheWell': 'Child', 'ForestTemple': 'Adult', 'FireTemple': 'Adult',
    'WaterTemple': 'Adult', 'ShadowTemple': 'Adult', 'SpiritTemple': 'Both',
    'IceCavern': 'Adult', 'GerudoTrainingGround': 'Adult', 'InsideGanonCastle': 'Adult',
}


class Estado:
    def __init__(self, itens):
        self.i = set(itens)

    def tem(self, *xs):
        return all(x in self.i for x in xs)

    def hook(self):
        return HOOK in self.i or LONG in self.i

    def forca(self, n):  # 1 bracelete (evento), 2 prata, 3 ouro
        nivel = 3 if GOLD in self.i else 2 if SILVER in self.i else 1 if 'ev:BraceleteGoron' in self.i else 0
        return nivel >= n


# Eventos: nome -> regra(Estado). Calculados em ponto fixo junto com os baus.
def _eventos():
    E = {}
    E['ev:Crianca'] = lambda s: True
    E['ev:Ocarina'] = lambda s: True                       # Saria na ponte
    E['ev:CantigaZelda'] = lambda s: True                  # castelo (crianca)
    E['ev:CancaoSaria'] = lambda s: s.tem('ev:Ocarina')
    E['ev:CancaoEpona'] = lambda s: s.tem('ev:Ocarina')
    E['ev:CancaoSol'] = lambda s: s.tem('ev:CantigaZelda')
    E['ev:Garrafa'] = lambda s: True                       # mulher das galinhas
    E['ev:EscudoDeku'] = lambda s: True                    # loja
    E['ev:BraceleteGoron'] = lambda s: s.tem('ev:CantigaZelda', 'ev:CancaoSaria')
    E['ev:Magia'] = lambda s: s.tem('ev:CantigaZelda') and (s.tem(BOMBS) or (s.tem('ev:Adulto', HAMMER)))
    E['ev:FogoDin'] = lambda s: s.tem('ev:CantigaZelda', BOMBS)
    # pedras espirituais = terminar as 3 masmorras de crianca
    E['ev:Esmeralda'] = lambda s: s.tem(KOKIRI, SLING, 'ev:EscudoDeku')
    E['ev:Rubi'] = lambda s: s.tem(BOMBS) and (s.tem(SLING) or s.tem(BOW)) and (s.forca(1) or s.tem(BOMBS))
    E['ev:Safira'] = lambda s: s.tem('ev:CantigaZelda', 'ev:Garrafa', BOOM)
    E['ev:Adulto'] = lambda s: s.tem('ev:Esmeralda', 'ev:Rubi', 'ev:Safira', 'ev:Ocarina')  # Espada Mestra
    E['ev:CancaoTempestade'] = lambda s: s.tem('ev:Adulto', 'ev:Ocarina')
    E['ev:TunicaGoron'] = lambda s: s.tem('ev:Adulto') and (s.tem(BOMBS) or s.tem(BOW))
    E['ev:FogoAzul'] = lambda s: s.tem('ev:Adulto', 'ev:CantigaZelda', 'ev:Garrafa')
    E['ev:TunicaZora'] = lambda s: s.tem('ev:FogoAzul')
    E['ev:CartaoGerudo'] = lambda s: s.tem('ev:Adulto', BOW) and s.hook()
    E['ev:Deserto'] = lambda s: s.tem('ev:CartaoGerudo', LENS, 'ev:Magia') and (s.tem(HOVER) or s.tem(LONG))
    # medalhoes = terminar os templos de adulto (mesmas regras dos baus de cada templo)
    E['ev:MedFloresta'] = lambda s: s.tem('ev:Adulto', BOW) and s.hook()
    E['ev:MedFogo'] = lambda s: s.tem('ev:TunicaGoron', HAMMER, BOMBS)
    E['ev:MedAgua'] = lambda s: s.tem('ev:TunicaZora', IRON, LONG, BOW, 'ev:CantigaZelda')
    E['ev:Noturno'] = lambda s: s.tem('ev:MedFloresta', 'ev:MedFogo', 'ev:MedAgua')
    E['ev:Requiem'] = lambda s: s.tem('ev:Deserto')
    E['ev:MedSombra'] = lambda s: s.tem('ev:Noturno', 'ev:FogoDin', 'ev:Magia', LENS, HOVER, BOMBS, BOW) and s.hook()
    E['ev:MedEspirito'] = lambda s: (s.tem('ev:Requiem', SILVER, MIRROR, BOMBS, BOW, LENS, 'ev:CantigaZelda', 'ev:Magia')
                                     and s.hook())
    E['ev:FlechaLuz'] = lambda s: s.tem('ev:MedSombra', 'ev:MedEspirito')
    E['ev:Ponte'] = lambda s: s.tem('ev:MedSombra', 'ev:MedEspirito')
    # vitoria: ponte + todas as provas do castelo + flecha de luz
    E['ev:VITORIA'] = lambda s: (s.tem('ev:Ponte', 'ev:FlechaLuz', BOW, GOLD, HAMMER, LENS, MIRROR, BOMBS,
                                       'ev:FogoAzul', 'ev:CantigaZelda', 'ev:Magia') and s.hook())
    return E


EVENTOS = _eventos()


def regra_entrada(area, s):
    """O que basta para chegar ao bau do item principal ORIGINAL da masmorra (no jogo original
    ele e alcancado sem esse item). Usada so para esse bau; os outros usam regra_masmorra."""
    a = s.tem('ev:Adulto')
    return {
        'InsideTheDekuTree': lambda: s.tem(KOKIRI, 'ev:EscudoDeku'),
        'DodongoCavern': lambda: s.forca(1) or s.tem(BOMBS),
        'InsideJabuJabuBelly': lambda: s.tem('ev:CantigaZelda', 'ev:Garrafa'),
        'BottomOfTheWell': lambda: s.tem('ev:CancaoTempestade', KOKIRI, 'ev:CantigaZelda'),
        'ForestTemple': lambda: a and s.hook(),
        'FireTemple': lambda: s.tem('ev:TunicaGoron', BOMBS),
        'WaterTemple': lambda: s.tem('ev:TunicaZora', IRON, 'ev:CantigaZelda') and s.hook(),
        'ShadowTemple': lambda: s.tem('ev:Noturno', 'ev:FogoDin', 'ev:Magia', LENS) and s.hook(),
        'SpiritTemple': lambda: s.tem('ev:MedEspirito'),
        'IceCavern': lambda: s.tem('ev:FogoAzul'),
        'GerudoTrainingGround': lambda: regra_masmorra(area, s),
        'InsideGanonCastle': lambda: s.tem('ev:Ponte', 'ev:Magia', BOW),
    }[area]()


def regra_masmorra(area, s):
    """Tudo o que a masmorra exige no jogo original (entrada + interior). Conservador."""
    a = s.tem('ev:Adulto')
    return {
        'InsideTheDekuTree': lambda: s.tem(KOKIRI, SLING, 'ev:EscudoDeku'),
        'DodongoCavern': lambda: s.tem(BOMBS) and (s.tem(SLING) or s.tem(BOW)),
        'InsideJabuJabuBelly': lambda: s.tem('ev:CantigaZelda', 'ev:Garrafa', BOOM),
        'BottomOfTheWell': lambda: s.tem('ev:CancaoTempestade', KOKIRI, LENS, 'ev:Magia', BOMBS),
        'ForestTemple': lambda: a and s.tem(BOW) and s.hook(),
        'FireTemple': lambda: s.tem('ev:TunicaGoron', HAMMER, BOMBS),
        'WaterTemple': lambda: s.tem('ev:TunicaZora', IRON, LONG, BOW, 'ev:CantigaZelda'),
        'ShadowTemple': lambda: s.tem('ev:MedSombra'),
        'SpiritTemple': lambda: s.tem('ev:MedEspirito'),
        'IceCavern': lambda: s.tem('ev:FogoAzul'),
        'GerudoTrainingGround': lambda: (s.tem('ev:CartaoGerudo', BOW, LONG, HAMMER, IRON, HOVER, LENS, SILVER,
                                               BOMBS, 'ev:Magia')),
        'InsideGanonCastle': lambda: s.tem('ev:Ponte', 'ev:FlechaLuz', BOW, LENS, HAMMER, MIRROR, BOMBS,
                                           'ev:FogoAzul', 'ev:Magia') and s.hook(),
    }[area]()


def regra_mundo(area, idade, s):
    """Baus fora de masmorras: acesso a area por idade + explosivo (muitos estao em grutas)."""
    if idade == 'Adult' and not s.tem('ev:Adulto'):
        return False
    bomba = s.tem(BOMBS) or (idade == 'Adult' and s.tem(HAMMER))
    r = {
        'KokiriForest': lambda: True,
        'LostWood': lambda: bomba,
        'SacredForestMeadow': lambda: bomba,
        'HyruleField': lambda: bomba,
        'KakarikoVillage': lambda: bomba and (idade == 'Child' or s.hook()),
        'Graveyard': lambda: s.tem('ev:CantigaZelda') and bomba,
        'DeathMountainTrail': lambda: bomba,
        'DeathMountainCrater': lambda: bomba and (idade == 'Child' or s.tem('ev:TunicaGoron')),
        'GoronCity': lambda: bomba and s.forca(1),
        'ZoraRiver': lambda: bomba,
        'ZoraDomain': lambda: s.tem('ev:CantigaZelda'),
        'ZoraFountain': lambda: s.tem('ev:CantigaZelda', IRON) and bomba,
        'GerudoValley': lambda: bomba and (idade == 'Child' or (s.tem('ev:CancaoEpona') and s.hook())),
        'GerudoFortress': lambda: s.tem('ev:CartaoGerudo'),
        'HountedWasteland': lambda: s.tem('ev:Deserto'),
        'DesertColossus': lambda: s.tem('ev:Requiem'),
    }.get(area)
    return bool(r and r())


# baus especiais com regra propria, pelo evento do bau
ESPECIAIS = {
    # lado crianca do Templo do Espirito (manopla de prata no original)
    'SageOfSpirit_NaboorIsTakenAway': lambda s: s.tem('ev:Requiem', KOKIRI) and (s.tem(SLING) or s.tem(BOOM)),
    # lado adulto (escudo espelhado no original): precisa da manopla de prata
    'SageOfSpirit_GetShield': lambda s: s.tem('ev:Requiem', SILVER, BOMBS) and s.hook(),
    # corrida do Dampe (adulto)
    'MiniGame_DampeRace_OpenGoalTBox': lambda s: s.tem('ev:Adulto'),
}


def acessivel(loc, s):
    """True se o bau e alcancavel no estado s (em alguma das idades dele)."""
    if loc['gyaml'].startswith('Obj_TBox_GlassTruth') and not s.tem(LENS, 'ev:Magia'):
        return False
    area = loc['area']
    if loc.get('regra_extra') and not s.tem(*loc['regra_extra']):
        return False
    if loc.get('evento') in ESPECIAIS:
        return ESPECIAIS[loc['evento']](s)
    if area in MASMORRA_IDADE:
        if loc['item'] in PROGRESSAO:  # bau do item principal original
            return regra_entrada(area, s)
        return regra_masmorra(area, s)
    for idade in ('Child', 'Adult'):
        if idade in loc['idades'] or 'Ambas' in loc['idades']:
            if regra_mundo(area, idade, s):
                return True
    return False


# eventos de historia presos a um bau: abrir o bau (qualquer item) dispara o evento
EVENTO_DO_BAU = {
    'SageOfWater_MelodyGet_Water': 'ev:SerenataAgua',
    'SageOfSpirit_NaboorIsTakenAway': 'ev:NabooruLevada',
}
