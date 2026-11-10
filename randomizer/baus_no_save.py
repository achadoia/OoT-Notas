"""Lista os baus de uma area com o estado (aberto/fechado) no save mais recente.
uso: python baus_no_save.py FireTemple"""
import sys, os, glob, mmh3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import ootlib as L
L.set_game(r"D:/Ocarina of Time/jogos/The Legend of Zelda Ocarina of Time [0400486024dec000][v131072]")

area = sys.argv[1]
saves = glob.glob(os.path.expandvars(r'%APPDATA%\eden\nand\user\save\*\*\0400486024DEC000\slot_*\progress.sav'))
save = max(saves, key=os.path.getmtime)
secoes, keys64, _ = L.read_save(save)
bools = secoes.get('Bool', {})
print('save:', save)
for rel in sorted(os.listdir(os.path.join(L.find('Banc/' + area)))):
    if not rel.endswith('.bcett.byml.zs'):
        continue
    by = L.byml(L.read(f'Banc/{area}/{rel}'))
    for a in by.get('Actors', []) or []:
        dyn = a.get('Dynamic') or {}
        if 'TBox' not in a['Gyaml'] or 'Drop__DropActor' not in dyn:
            continue
        h = a['Hash']
        flag = mmh3.hash('IsTreasureBoxOpen.%d' % h, 0, signed=False)
        aberto = bools.get(flag)
        estado = 'ABERTO' if aberto else ('fechado' if flag in bools else 'fechado?')
        print(f"{rel[:-15]:28s} {h:20d} sala {dyn.get('DefaultDungeonRoomIndex', '-'):>3} {estado:8s} "
              f"{dyn['Drop__DropActor']:28s} {dyn.get('GetEventName', '')}")
