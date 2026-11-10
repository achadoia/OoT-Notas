"""Mod de TESTE: os 3 baus fechados da sala 8 do Templo do Fogo (rupias no original)
passam a dar Botas de Pouso, Flecha de Gelo e Rupia de Ouro."""
import os, sys, glob, shutil, time
sys.path.insert(0, os.path.dirname(__file__))
import modfs as M

TROCAS = {
    862385681502746018: 'Item_HoverBoot',       # era TBox_Rupee_Purple
    17001858340376096722: 'Item_Arrow_Ice',     # era TBox_Rupee_Red
    15073195886628236505: 'TBox_Rupee_Gold',    # era TBox_Rupee_Red
}

# backup dos saves antes do teste
saves = os.path.expandvars(r'%APPDATA%\eden\nand\user\save\0000000000000000\EFEB185079F7FA599D416B2F53C3BC5D\0400486024DEC000')
bk = r'D:\OoT-Notas\data\backup-saves\antes-teste-fogo-' + time.strftime('%Y%m%d-%H%M%S')
shutil.copytree(saves, bk)
print('backup dos saves:', bk)

mod = M.limpar_mod('Randomizer-Teste')
pasta = os.path.dirname(M.L.find('Banc/FireTemple/x') or M.L.find('Banc/FireTemple'))
for nome in os.listdir(M.L.find('Banc/FireTemple')):
    if not nome.endswith('.bcett.byml.zs'):
        continue
    c = M.Cena(f'Banc/FireTemple/{nome}')
    for h, item in TROCAS.items():
        try:
            antes = c.trocar_drop(h, item)
            print(f'{nome}: {h} {antes} -> {item}')
        except KeyError:
            pass
    if c.mudou:
        print('gravado', c.gravar(mod))
