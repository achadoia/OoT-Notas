# OoT-Notas — Randomizer e engenharia reversa do Zelda: Ocarina of Time (Remake)

O **motor do randomizer** e as ferramentas que leem os arquivos do *Ocarina of Time* Remake. Ele roda dentro do jogo nativo de
PC pelo mod [**Hookshot-Zelda**](https://github.com/achadoia/Hookshot-Zelda), que tem o menu na tela de título, o mapa F7
estilo MapGenie e o tracker de itens.

![Menu do Randomizer no jogo](https://raw.githubusercontent.com/achadoia/Hookshot-Zelda/master/docs/prints/randomizer-menu.png)

## O Randomizer

Inspirado no randomizer do *Ship of Harkinian* (o mesmo desenho: *Assumed Fill*, esferas, restrições por tipo de local), com
**código próprio** adaptado à engine do Remake.

```
python randomizer/randomizer.py --seed MINHA-SEED --embaralhar masmorras,mundo,npcs,musicas,lojas --saida <pasta>
python randomizer/randomizer.py --vanilla          # confere a lógica com tudo no lugar original
```

| `--embaralhar` | Locais |
|---|---|
| `masmorras` | 56 baús de masmorra |
| `mundo` | 42 baús do mundo |
| `npcs` | 48 entregas de NPCs e quests (Grandes Fadas, ocarinas, carta da Zelda, Flechas de Luz, túnicas, garrafas, minigames, trocas...) |
| `musicas` | os 12 professores de música |
| `lojas` | as vitrines das lojas (`Shop_*`) e as mercadorias dos Deku vendedores |

Saída: `romfs\` (só os arquivos mudados), `rsizetable.zs` (a ResourceSizeTable com as entradas aumentadas), `spoiler.txt` /
`spoiler.json` (o caminho por esferas e onde caiu cada item).

### Como o Remake entrega os itens (o que foi descoberto)

- **Baús**: `Dynamic.Drop__DropActor` do ator do baú nas cenas `Banc/<Area>/*.bcett.byml.zs` (BYML v7).
- **NPCs**: os fluxos de evento (`Event/EventFlow/*.bfevfl`, BFEVFL v4 — `randomizer/evfl.py` lê e edita) chamam subfluxos
  comuns passando o item: `Dm_SY_GetInEvent` (`ActorName`: modelo, fanfarra, janela e inventário), `GetPouchContent`,
  `NpcCommon` (`ReceiveItem`). Trocar esse parâmetro troca o item.
- **Músicas**: `Dm_SY_Ocarina` tem uma `PouchSystemActor.EventTriggerAddOrRemovePouchContent` por música (o professor escolhe pelo
  `MelodyType`) e cada cena `Dm_MelodyGet_*` também dá a música por `GetPouchContent`.
- **"Já entreguei?"**: quase sempre flags próprias (`HavePlayedEvent.*`, `<Npc>_IsGetHeartPiece`...). Onde é `IsGet.<item>`
  (só existem 43 dessas flags), a pergunta é reescrita para o item novo.
- **Lojas**: atores `Shop_<item>` (com `ShopItemIndex`); Deku vendedores: `ScrubBusiness_ShopItemActorName0..2`.
- **Editar um .bfevfl sem reescrever tudo**: a string nova vai no fim do arquivo e só o ponteiro muda (ele já está na tabela de
  relocação); o tamanho no cabeçalho acompanha.
- **ResourceSizeTable**: o motor descarta um arquivo maior que a sua entrada (margem de ~284 bytes) — a seed grava a tabela
  com as entradas aumentadas.

### Lógica (`randomizer/logica.py`)

Conservadora e sem truques: cada masmorra exige o que o jogo original exige; músicas, magia, Fogo de Din, cartão Gerudo,
bracelete, ocarinas, carta da Zelda, garrafa, túnicas e Flechas de Luz são **itens dados por locais**, então a lógica sabe
quando cada um fica disponível (ex.: sem a carta da Zelda o guarda não abre o portão da montanha; a Porta do Tempo pede a
Canção do Tempo). Minigames e trocas, que podem repetir o prêmio, só recebem itens que não são de progressão.

## Ferramentas (`tools/`)

- `ootlib.py` — zstd com os dicionários do jogo, SARC, BYML (BE/LE), murmur3.
- `bntx.py` — texturas BNTX do Switch 2 (ASTC + swizzle) → PNG.
- `gerar_notas.py`, `icones_notas.py` — os dados e ícones do mapa F7.
- [`LEIA-ME.md`](LEIA-ME.md) — as notas de engenharia reversa (GameData, saves, flags dos baús, skulltulas...).

**Nenhum arquivo do jogo está neste repositório**: `data/` é gerado a partir da RomFS local e fica no `.gitignore`.
*The Legend of Zelda* é da Nintendo.

Mod by **@AchadoIA**.
