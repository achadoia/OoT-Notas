# OoT-Notas: engenharia reversa do Zelda: Ocarina of Time Remake (Switch 2)

Base para dois projetos:
1. **Notas**: painel no NS2-IA (estilo Zelda Notes) mostrando checks, missões, o que já foi pego e o que falta.
2. **Randomizer**: inspirado no randomizer do Ship of Harkinian (OoT 1998), adaptado à engine do Remake.

O jogo é o título `0400486024DEC000`, versão de update 131072 (v1.1.0, GameDataList `Product.110`).
RomFS extraído pelo NS2-IA em `D:\Ocarina of Time\jogos\The Legend of Zelda Ocarina of Time [0400486024dec000][v131072]\`
(`base\romfs`, `updates\131072\romfs`; o update tem prioridade).

**Nada do jogo vai para o git**: `data\` é gerado a partir do RomFS local e fica no `.gitignore`.

## Engine

É a mesma família de engine do Tears of the Kingdom:
- Arquivos `.zs` são zstd. Alguns usam os dicionários de `Pack/ZsDic.pack.zs`, que é um SARC.
- Os BYML são **big-endian** (`BY`, versão 7). O do TotK é little-endian. O `ootlib.Byml` aceita os dois.
- Hash dos nomes: **murmur3_32, seed 0** (conferido com os `RawValues`/`Values` dos Enum).
- Cenas ficam em `Banc/<Area>/<Area>_<Child|Adult>_<Static|Dynamic>.bcett.byml.zs`
  (160 arquivos). Cada ator tem `Gyaml`, `Hash` (u64, ID da instância), `Translate` e `Dynamic`.

## GameDataList (`GameData/GameDataList.Product.110.byml.zs`)

Estrutura: `Data` → listas por tipo, com `Hash`, `DefaultValue`, `ResetTypeValue`, `SaveFileIndex`.

| Tipo | Quantidade | Observação |
|---|---|---|
| Bool | 11292 | 10212 no `progress.sav` (SaveFileIndex 0) |
| Bool64bitKey | 11657 | um por ator das fases (Hash = `Hash` do ator no Banc) |
| BoolExp | 884 | expressões (SaveFileIndex -1, não salvas) |
| Int | 1259 | contadores (inimigos, minigames…) |
| Struct | 874 | |
| Enum | 130 | `RawValues` têm os nomes |

Os nomes não estão no GameDataList. O `harvest.py` varre as strings do RomFS e casa os hashes:
3709 de 11292 Bool, 528 BoolExp e 281 Int ganharam nome (`data\names.json`).
Prefixos úteis: `IsGet.Item_*`, `Get_*`, `HaveTalked*`, `HavePlayedEvent.*`, `<Masmorra>_Room*_Clear`,
`SubEvent_*`, `MiniGame_*`, `Sage*`, `DefeatedEnemyNum.*`, `KakarikoVillage_GatheringTokenGold_GetReward*`.

## Save (`progress.sav`)

Fica em `%APPDATA%\eden\nand\user\save\0000000000000000\<user>\0400486024DEC000\slot_00..05\`
(também há `caption.sav` e `option.sav`, no mesmo formato).

- Cabeçalho: `u32 0x01020304`, `u32 versão 0x2d80eb`, `u32 fim da tabela 0x175d8`.
- A partir de 0x28 vêm pares `(u32 hash, u32 valor)`. Um hash 0 marca o início de uma seção, e o
  valor é o id dela (ver `ootlib.SECTION_TYPES`: 0 Bool, 2 Int, 6 Enum, 20 UInt, 32 Bool64bitKey…).
- Bool e Int ficam direto no valor. Arrays e strings guardam um offset para a área de dados.
- **Bool64bitKey** (seção 32) tem 1 entrada, e o valor é o offset de uma **lista de u64 com as chaves
  LIGADAS**, terminada por 0. Cada chave é o `Hash` de um ator do Banc já pego, aberto ou quebrado.
  O slot 04 tem 249 chaves, entre elas 39 Skulltulas Douradas, 7 Pedaços de Coração e 5 Recipientes.

## Checks mapeados nos Banc (`data\banc_flags.json`)

Atores com flag de 64 bits: 3871. Principais Gyaml:
- `Enemy_Skulltula_Gold` 114 posições (o original tem 100 tokens; há repetições criança/adulto)
- Baús: `Obj_TBox_A_01` 107, `_NoBake` 49, `Obj_TBox_A_02` 28 (+17 NoBake), `Obj_TBox_GlassTruth_A_01` 11, `A_04`, `A_06`, `Obj_HrlCity_Shop_TBox_A_01` 10
- `Obj_Heart_Piece` 24 (os outros 12 vêm de NPCs/minigames: são flags nomeadas) · `Obj_Heart_Container` 8
- `Obj_RupeeToken_Silver` 85 (rupias prateadas) · `Enemy_Scrub_Business*` (vendedores Deku) · `WallCrack` 39 · `Obj_FairySpirit` 113 (fadas) · lojas `Shop_*`

Pendente: confirmar que baú aberto = chave ligada (o slot 04 tem poucas, então talvez use `ExtraByte`),
ler o conteúdo dos baús (`Dynamic`) e dar nome em pt-BR a cada check (área + sala).

## Ferramentas (`tools\`)

- `ootlib.py`: zstd/ZsDic, SARC, BYML (BE/LE, mapas de hash 0x20/0x21) e `read_save()`.
- `harvest.py`: strings do RomFS → murmur3 → `data\names.json` (+ `strings.txt`, 100 MB). Leva uns 5 min, 10 processos.
- `scan_banc.py`: atores do Banc com Bool64bitKey → `data\banc_flags.json`.

Dependências: `python -m pip install zstandard mmh3`.

## Próximos passos

### Notas (painel no NS2-IA)
1. Gerar `notas.json`: categorias (Skulltulas, Corações, Baús, Masmorras, Canções, Itens, Missões), cada check com hash ou chave de 64 bits e nome em pt-BR.
2. Dock Qt no NS2-IA (`src/yuzu/fritchii/`, menu Exibir) com `QFileSystemWatcher` nos `progress.sav`, usando o slot mais recente.
3. Depois, ler o GameDataMgr direto da memória do jogo para atualizar ao vivo.

### Randomizer (ideia do Ship of Harkinian)
O SoH separa **locais** (checks) de **itens**, tem uma lógica de acesso (o que cada local exige),
preenche os itens com *assumed fill* garantindo que o jogo pode ser zerado e gera um *spoiler log*.
No Remake, a forma natural é:
- Locais = atores do Banc (baús via `Dynamic`, skulltulas, corações) + flags de NPC/evento.
- Aplicar = sobrepor os `.bcett.byml.zs` alterados (LayeredFS do emulador, `load\0400486024DEC000\<mod>\romfs`).
  Itens dados por NPCs/eventos ficam nos EventFlow/AINB.
- Lógica = escrever as regras por área, como o SoH faz (idade, itens, canções).
