# Randomizer do OoT Remake (NS2-IA)

Desenho estudado no Ship of Harkinian 9.3.1 (ver `ANALISE-SOH.md`); código próprio
(o repositório do SoH não tem licença, nada foi copiado).

## Como o Remake entrega itens de baú
Cada baú é um ator `Obj_TBox_*` nos arquivos de cena `Banc/<Area>/<Area>_[Child|Adult]_[Static|Dynamic].bcett.byml.zs`.
O item fica em `Dynamic.Drop__DropActor` (nome do ator do item, ex. `Item_Hookshot`, `TBox_Rupee_Red`).
Outros campos: `GetEventName` (evento de história preso ao baú: fica no LOCAL, só o item muda),
`Drop__CheckActor` + `Drop__DropActor_Substitute` (troca se o jogador já tem o item),
`IsEnableRepeatOpen` (minigames). O mesmo `Hash` em Child e Adult = o mesmo baú.

## Arquivos
- `bymlrw.py` – BYML v7 sem perda (lê/grava; ida e volta testada nos 160 arquivos de cena).
- `modfs.py` – grava cenas modificadas como mod LayeredFS em `%APPDATA%\eden\load\0400486024DEC000\<mod>\romfs`, recomprimindo com o mesmo dicionário zstd.
- `extrair_locais.py` – inventário: `data/rando_locais.json` (203 baús únicos).
- `logica.py` – lógica glitchless conservadora: eventos (NPC/história no lugar original), regra de entrada x regra completa por masmorra, regras por área e idade.
- `randomizer.py` – AssumedFill + verificação por esferas (todos os baús alcançáveis + vitória + ordem dos progressivos), spoiler, mod.
- `teste_fogo.py` – mod de TESTE (3 baús fechados da sala 8 do Templo do Fogo).

## Uso
    python randomizer.py --vanilla          # valida a lógica com tudo no lugar original
    python randomizer.py --seed minha-seed  # gera spoiler + mod 'Randomizer'

## Escopo da versão 1
98 baús embaralhados; 105 fixos: chaves, chave do chefe, mapa, bússola (lugar original),
minigames repetíveis, DreamWorld, baús de escudo (A_06), sementes do negócio Deku.
Fora (por enquanto): itens de NPC, músicas, corações soltos, skulltulas, lojas, entradas.

## Pendências
1. Confirmar no jogo que trocar `Drop__DropActor` funciona (teste do Templo do Fogo).
2. Confirmar baús com evento (Espada Kokiri, Botas de Ferro/Serenata) com outro item.
3. Gancho Longo sem Gancho / Manopla de Ouro sem Prata: a geração já força a ordem.
4. Save separado para o modo randomizer + seletor no NS2-IA.

## Status 2026-11-10 — PAUSADO (removido do NS2-IA)

O mod gerado (48 arquivos de cena via LayeredFS) deixou o jogo em **tela preta**
no emulador: menu so com a logo, sem cenario, e travado depois de "Novo jogo".
Provavel causa: alguma cena reescrita pelo bymlrw.py/modfs.py que o jogo nao aceita
(investigar comparando cena por cena antes de reusar).

- Seletor NORMAL/RANDOMIZER do NS2-IA revertido (commit bdccb015b0 no NS2-IA-codigo).
- Ultimo mod gerado guardado em data\mod-randomizer-arquivado-20261110 (seed Ocarina-Sheik-325).
- Plano: reaproveitar logica.py / desenho do SoH numa futura **versao nativa de PC**,
  onde mexer nos arquivos e mais facil que no emulador.
