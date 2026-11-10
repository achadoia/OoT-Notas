"""Icones do painel Notas do Zelda (NS2-IA), tirados do RomFS do proprio usuario.

Saida: <NS2-IA>\\notas\\0400486024DEC000\\icones\\
  <categoria>.png        icone do marcador (128x128, fundo transparente)
  <categoria>_pego.png   versao "ja pego" (quando o jogo tem uma; senao o painel esmaece)
  link_crianca.png / link_adulto.png   retrato do Link no mapa

Retrato do Link: o jogo nao tem foto do Link na UI. Se existirem imagens em
D:\\OoT-Notas\\data\\wiki-link\\crianca.png / adulto.png (renders salvos pelo usuario, ex. da Zelda Wiki),
recorta o rosto e faz um medalhao; senao usa a tunica do jogo como medalhao provisorio.
uso: python icones_notas.py [pasta_ns2ia]"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
import ootlib as L  # noqa: E402
import bntx  # noqa: E402

JOGO = r'D:\Ocarina of Time\jogos\The Legend of Zelda Ocarina of Time [0400486024dec000][v131072]'
NS2 = sys.argv[1] if len(sys.argv) > 1 else r'D:\NS2-IA'
OUT = os.path.join(NS2, 'notas', '0400486024DEC000', 'icones')
WIKI = os.path.join(os.path.dirname(__file__), '..', 'data', 'wiki-link')
L.set_game(JOGO)

UI = 'UI/Layout2Archive/Common.Product.100.Nin_Ounce_NVN2.bntx.zs'
ui_raw = L.read(UI)
ui_idx = {t['name']: i for i, t in enumerate(bntx.textures(ui_raw))}


def ui(nome):
    return bntx.decode(ui_raw, ui_idx[nome])[0].convert('RGBA')


def item(nome):
    return bntx.decode(L.read('UI/Tex/Icon/%s.bntx.zs' % nome))[0].convert('RGBA')


def medalhao(img, cor, tam=128, borda=10, fundo=(30, 30, 28, 255), cobrir=False):
    """Circulo com aro na cor da categoria e a imagem dentro (no estilo dos MapIcon do jogo)."""
    esc = 4
    T = tam * esc
    out = Image.new('RGBA', (T, T), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    d.ellipse((2 * esc, 2 * esc, T - 2 * esc, T - 2 * esc), fill=(58, 22, 10, 255))  # contorno escuro
    d.ellipse((5 * esc, 5 * esc, T - 5 * esc, T - 5 * esc), fill=cor)
    r0 = (5 + borda) * esc
    d.ellipse((r0, r0, T - r0, T - r0), fill=fundo)
    lado = T - 2 * r0
    if cobrir:
        im = img.resize((lado, lado), Image.LANCZOS)
    else:
        im = img.copy()
        im.thumbnail((int(lado * 0.86), int(lado * 0.86)), Image.LANCZOS)
    mask = Image.new('L', (lado, lado), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, lado - 1, lado - 1), fill=255)
    camada = Image.new('RGBA', (lado, lado), (0, 0, 0, 0))
    camada.alpha_composite(im, ((lado - im.width) // 2, (lado - im.height) // 2))
    camada.putalpha(Image.composite(camada.getchannel('A'), Image.new('L', (lado, lado), 0), mask))
    out.alpha_composite(camada, (r0, r0))
    return out.resize((tam, tam), Image.LANCZOS)


def rosto(caminho):
    """Recorta a cabeca de um render de corpo inteiro (fundo transparente): quadrado no topo do recorte."""
    im = Image.open(caminho).convert('RGBA')
    x0, y0, x1, y1 = im.getchannel('A').point(lambda a: 255 if a > 40 else 0).getbbox()
    alt = y1 - y0
    lado = int(alt * 0.30)
    # centro horizontal da cabeca = centro da massa opaca na faixa do topo
    faixa = im.getchannel('A').crop((x0, y0, x1, y0 + lado))
    cols = [sum(1 for v in faixa.crop((i, 0, i + 1, faixa.height)).getdata() if v > 40) for i in range(faixa.width)]
    tot = sum(cols) or 1
    cx = x0 + sum(i * c for i, c in enumerate(cols)) / tot
    cx0 = int(cx - lado / 2)
    cy0 = max(0, y0 - int(lado * 0.04))
    return im.crop((cx0, cy0, cx0 + lado, cy0 + lado))


def salvar(img, nome):
    # tira a margem transparente e deixa quadrado (os MapIcon do jogo tem bastante folga)
    bb = img.getchannel('A').point(lambda a: 255 if a > 8 else 0).getbbox()
    if bb:
        img = img.crop(bb)
        lado = max(img.size)
        q = Image.new('RGBA', (lado, lado), (0, 0, 0, 0))
        q.alpha_composite(img, ((lado - img.width) // 2, (lado - img.height) // 2))
        img = q.resize((128, 128), Image.LANCZOS)
    img.save(os.path.join(OUT, nome + '.png'))
    print('ok', nome)


def main():
    os.makedirs(OUT, exist_ok=True)
    # icones de mapa do proprio jogo (com versao "ja pego")
    salvar(ui('MapIconCollectSkullSign_00'), 'skulltula')
    salvar(ui('MapIconCollectSkullSignCheck_00'), 'skulltula_pego')
    salvar(ui('MapIconCollectHeartPiece_00'), 'coracao')
    salvar(ui('MapIconCollectHeartPieceCheck_00'), 'coracao_pego')
    salvar(ui('MapIconTreasure_00'), 'bau_item')
    salvar(ui('MapIconTreasure_01'), 'bau_item_pego')
    # icones de item do jogo em medalhao na cor da categoria
    salvar(medalhao(item('Item_Dungeon_SmallKey'), '#8fd14f'), 'bau_chave')
    salvar(medalhao(item('Obj_Rupee_Red'), '#9aa5b1'), 'bau_rupia')
    salvar(medalhao(item('Obj_Rupee_Purple'), '#d6dde6'), 'rupia_prata')
    salvar(medalhao(item('Item_DekuNut'), '#c58b4b'), 'deku')
    salvar(medalhao(item('Item_Bomb'), '#b07cff'), 'parede')
    # recipiente: peca de coracao do jogo com aro vermelho
    salvar(medalhao(ui('CollectHeartPiece_00') if 'CollectHeartPiece_00' in ui_idx else item('Item_AgonyStone'),
                    '#e0245e'), 'recipiente')
    # Link
    for era, render, tunica in (('crianca', 'crianca.png', 'Obj_Armor_Child_Normal'),
                                ('adulto', 'adulto.png', 'Armor_Adult_Normal')):
        p = os.path.join(WIKI, render)
        if os.path.exists(p):
            salvar(medalhao(rosto(p), '#3dd65c', borda=7, fundo=(232, 214, 160, 255), cobrir=True), 'link_' + era)
        else:
            print('  (sem %s: usando a tunica do jogo)' % p)
            salvar(medalhao(item(tunica), '#3dd65c', borda=7), 'link_' + era)


if __name__ == '__main__':
    main()
