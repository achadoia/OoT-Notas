# Análise de design: randomizer do Ship of Harkinian 9.3.1 "Dewey Bravo"

Fonte: HarbourMasters/Shipwright, tag `9.3.1`, lida em clone esparso (nada foi executado).
O repositório **não tem licença**, então isto é só uma descrição de design, sem código copiado.
Prefixo dos caminhos: `R/` = `soh/soh/Enhancements/randomizer/`.

Mapa rápido do código:
- `R/3drando/` tem o "motor" herdado do OoT3D Randomizer: `fill.cpp`, `item_pool.cpp`, `playthrough.cpp`, `hints.cpp`, `spoiler_log.cpp`, `starting_inventory.cpp`, `shops.cpp`.
- `R/location_access/{root.cpp, overworld/*.cpp, dungeons/*.cpp}` é o grafo de lógica: cerca de 1069 regiões.
- `R/location_list.cpp` é a tabela estática de checks, com cerca de 745 entradas `locationTable[RC_…]`.
- `R/item_list.cpp` é a tabela de itens.
- `R/logic.cpp/.h` tem os helpers `HasItem`, `CanUse` etc. e um SaveContext simulado.
- `R/settings.cpp` tem as opções, os defaults e cerca de 216 tricks.
- `R/SeedContext.cpp` guarda o estado da seed, o pool de locais e os overrides.
- `R/hook_handlers.cpp`, `R/randomizer.cpp` e `R/savefile.cpp` cuidam do runtime.

---

## 1. Pipeline de ponta a ponta

1. **Seed.** Em `R/3drando/menu.cpp:14-45` (`GenerateRandomizer`), uma seed vazia vira 10 dígitos aleatórios. A string passa por hash, e esse hash é a seed numérica.
2. **Settings → hash final.** `R/3drando/playthrough.cpp:17-66`:
   - `Random_Init(seed)` para resolver opções do tipo "random".
   - `FinalizeSettings` (`R/settings.cpp:2643`) normaliza o que é incompatível. Por exemplo, força começar como criança se a Door of Time está fechada sem ocarina embaralhada; liga `RSK_SHUFFLE_ENTRANCES` se qualquer sub-ER estiver ligado; marca locais excluídos; aplica tricks.
   - Todas as opções viram texto, concatenado à seed e passado por hash de novo. `Random_Init(finalHash)` em `playthrough.cpp:64-65`.
   - Conclusão: **mesma seed + mesmas opções = mesmo resultado**, e qualquer mudança de opção muda tudo.
   - O RNG é um único estado global (`R/rng.h:10-47`) com `Random`, `RandomElement` e `Shuffle`.
3. **Fill.** `R/3drando/fill.cpp:1287-1516` (`Fill()`), detalhado na seção 2.
4. **Playthrough, WotH e barren.** `fill.cpp:1475-1491`.
5. **Overrides.** `Context::CreateItemOverrides` (`R/SeedContext.cpp:339`) só gera os disfarces de ice trap (modelo e nome falsos).
6. **Hints.** `CreateAllHints` (`R/3drando/hints.cpp:832`) e `CreateWarpSongTexts`.
7. **Spoiler log em JSON.** `SpoilerLog_Write` (`R/3drando/spoiler_log.cpp:292`). O nome do arquivo são os índices dos ícones de hash.
8. **Runtime.** O jogo não é "patcheado". O JSON do spoiler **é** o arquivo da seed:
   - `Context::ParseSpoiler` (`SeedContext.cpp:405`) e `ParseItemLocationsJson` (`:438`) recarregam `locations → item/price/model`.
   - Cada check é identificado por **(actorId, sceneId, params)** na tabela estática. Exemplos: o baú de Mido usa `ACTOR_EN_BOX, SCENE_MIDOS_HOUSE, 22944` (`location_list.cpp:156`); o PoH do Lago usa `ACTOR_EN_ITEM00, SCENE_LAKE_HYLIA, 7686, flag 0x1E` (`:195`).
   - O lookup é `GetCheckObjectFromActor` (`R/randomizer.cpp:681-823`), que trata casos especiais por cena e depois usa o multimap `CheckFromActorMultimap`.
   - Hooks "VB" (vanilla behavior) trocam a entrega:
     - **Baú:** `VB_GIVE_ITEM_FROM_CHEST` (`R/hook_handlers.cpp:1072-1087`) cancela o item vanilla se o local está embaralhado e entrega o item da seed.
     - **Item freestanding (EnItem00):** `VB_ITEM00_DESPAWN` (`:1195-1214`) troca o PoH/chave por um dummy que desenha o item randomizado, com `GetFinalGIEntry` (`SeedContext.cpp:375`). `VB_GIVE_ITEM_FROM_ITEM_00` (`:1323`) marca a flag e dá o item.
   - Para não depender das flags vanilla, existe um espaço próprio de flags `RandomizerInf` (`R/RCToRandInf.cpp`, `Flags_SetRandomizerInf`).
   - Itens que "não podem ser obtidos" (ex.: item de criança na seed errada) viram rupia azul, em `GetFinalGIEntry` (`SeedContext.cpp:383-389`).
   - O save inicial recebe itens iniciais e flags de mundo aberto em `R/savefile.cpp:126` (`SetStartingItems`): floresta aberta em `:470`, Door of Time em `:647`.

## 2. Algoritmo de FILL

Ordem fixa dentro de `Fill()` (`fill.cpp:1287+`), com **até 5 tentativas globais** (`:1291`). Cada tentativa reconstrói tudo do zero.

1. `RegionTable_Init`, `GenerateLocationPool` (`SeedContext.cpp:154`: filtra os locais por setting e por dungeon vanilla/MQ), `GenerateItemPool` (`item_pool.cpp:144`) e `GenerateStartingInventory`.
2. **Locais excluídos** recebem junk antes de tudo (`FillExcludedLocations`, `fill.cpp:1052` e `:1302`).
3. **Entrance shuffle**, se ligado. Antes, o pool recebe itens de loja temporários, "pior caso shopsanity" (`:1307`). Se o ER falhar, a tentativa conta como falha (`:1310`).
4. **Lojas.** Itens vanilla de loja, ou parte deles via `AssumedFill` nos slots que sobraram. Depois vêm os preços de lojas, scrubs e mercadores (`:1328-1410`).
5. **Recompensas de dungeon** (`RandomizeDungeonRewards`, `:978`):
   - Link's Pocket ganha uma pedra ou medalhão conforme a opção.
   - Light Medallion vai para Rauru quando aplicável.
   - Em "End of Dungeons" usa `AssumedFill` restrito aos locais de boss.
6. **Own Dungeon** (`RandomizeOwnDungeon`, `:1064`): chaves pequenas, chave do chefe e recompensa no mesmo `AssumedFill`, restritos aos locais da área da dungeon, excluindo locais reservados a músicas. Mapa e bússola vêm depois, em separado.
7. **Músicas**, quando "Song Locations" ou "Dungeon Rewards": `AssumedFill(songs, songLocations)` (`:1421-1449`).
8. **Any Dungeon / Overworld** (`RandomizeDungeonItems`, `:1133`): agrupa chaves, chaves de chefe, a chave do Ganon, chaves de Gerudo, recompensas e peças de triforce. Primeiro roda o pool "any dungeon", depois o "overworld", depois mapas e bússolas.
9. **Link's Pocket "Advancement"** (`:1239`).
10. **Todos os demais itens de progressão** (`IsAdvancement()`): `AssumedFill(…, allLocations)` (`:1465`).
11. **O resto** (junk, corações, etc.): `FastFill` puramente aleatório nos locais vazios (`:1471`, função em `:835`). Se faltarem itens, completa com `GetJunkItem`.

**AssumedFill** (`fill.cpp:857-956`), comentado no código como "do OoT Randomizer":
- Se houver mais itens que locais, falha.
- Se `No Logic` estiver ligado, vira FastFill.
- Até **10 retries locais** (`:882`). Em cada um:
  - Embaralha os itens a colocar.
  - Para cada item retirado do fim da lista:
    - `logic->Reset()`.
    - Aplica o efeito de **todos os itens ainda não colocados**: os restantes deste lote e os itens de progressão que ainda estão no `itemPool` global (`:906-912`).
    - Roda `ReachabilitySearch(allowedLocations)` e recebe os locais vazios alcançáveis.
    - Se a lista estiver vazia, desfaz todos os locais preenchidos neste lote e recomeça.
    - Senão sorteia um local uniformemente (`RandomElement`) e coloca o item.
  - Se **All Checks Reachable estiver desligado** (o default), depois de cada colocação chama `CheckBeatable()`. Se o jogo já for zerável, o resto do lote vai por FastFill (`:946-951`).
- Esgotados os 10 retries, `placementFailure` faz a tentativa global falhar.

Restrições de tipo (chaves na própria dungeon, músicas em locais de música, lojas) não são "regras" dentro do fill. São apenas **listas de locais permitidos diferentes** passadas ao mesmo `AssumedFill`, executadas na ordem do mais restrito para o mais livre.

## 3. Modelo de lógica

- **Região** (`R/location_access.h:139+`): nome, cena, `timePass`, conjunto de áreas (para hints), **eventos**, **locais** e **saídas**. Cada região guarda 4 bits de acesso: `childDay`, `childNight`, `adultDay`, `adultNight`.
- **Condições são lambdas**, declaradas com macros:
  - `LOCATION(RC, cond)` em `location_access.h:69`.
  - `ENTRANCE(RR, cond)` em `R/entrance.h:43`.
  - `EVENT_ACCESS(LOGIC_X, cond)` em `location_access.h:22`.
  - A condição também é guardada como string, para debug e tracker. Exemplo real: `R/location_access/dungeons/forest_temple.cpp:22-60`.
- **Helpers** em `R/logic.cpp`:
  - `HasItem` (`:24`) lê um **SaveContext simulado**. `ApplyItemEffect` (`:2205`) escreve nesse save falso quando um item é "coletado".
  - `CanUse` (`:539`) é `HasItem` mais `ItemUseAllowed` mais restrição de idade. Arco, hookshot, martelo e botas exigem `IsAdult`; magia exige `CanUse(RG_MAGIC_SINGLE)`.
  - Há dezenas de helpers semânticos: `CanKillEnemy` (`:758`), `CanPassEnemy`, `CanBreakPots`, `HasExplosives`, `BlastOrSmash`, `CanHitSwitch`, `EffectiveHealth` (`:1719`), `WaterLevel` etc.
  - 9.3.x também tem "habilidades" embaralháveis (`RG_CLIMB`, `RG_OPEN_CHEST`, `RG_CRAWL`, nadar, agarrar), que viram flags RandInf (`logic.cpp:~1967`).
- **Eventos** (`LOGIC_*`) são booleanos (`logic.h:186`, `inLogic[]`), ligados quando a condição passa em uma região alcançada (`Region::UpdateEvents`).
- **Idade e hora:** cada condição é avaliada 4 vezes, uma por combinação idade×hora com acesso na região pai (`location_access.cpp:45-58`). Na propagação por saídas (`fill.cpp:82-109`, `UpdateToDAccess`), a hora vira dia+noite em regiões com `timePass` (`location_access.cpp:433`).
  - **Viagem no tempo:** `PropagateTimeTravel` (`fill.cpp:63-79`). Se `RR_TOT_BEYOND_DOOR_OF_TIME` é alcançável com uma idade, a raiz ganha a outra idade.
  - A porta (`R/location_access/overworld/temple_of_time.cpp:41`) depende da setting de Door of Time ou de Song of Time + 3 pedras + Ocarina of Time. A Master Sword fica atrás da porta (`:46`).
  - "Pode como qualquer idade" usa `AnyAgeTime(fn)` (`location_access.h:226`, `location_access.cpp:856`).
- **Raiz** (`R/location_access/root.cpp`): spawns de criança e adulto, warps de música e eventos derivados de settings (carpinteiros livres, Kakariko aberto, etc.). Os locais "virtuais" `RC_WINCON`, `RC_GANONS_BOSS_KEY` e `RC_GANON_SOUL` ficam aqui com `CanTriggerX()`.
- **Níveis de lógica:**
  - Glitchless com tricks individuais (`OPT_TRICK`, ~216 em `settings.cpp`, lidos com `ctx->GetTrickOption(RT_…)`).
  - `RSK_NO_LOGIC` (`settings.cpp:1477`): todas as condições retornam `true` (`location_access.h:35-39`, `:84-89`) e o fill vira FastFill.
  - Glitches estão **stubados**: `CanDoGlitch` sempre `&& false` (`logic.cpp:736-750`).
  - `VanillaFill` (`fill.cpp:1258`) existe, mas não é chamado.

## 4. Como garantem seed zerável / sem softlock

- **Busca:** `ReachabilitySearch` (`fill.cpp:526`) é um ponto fixo. Faz loop sobre o pool de regiões; processa eventos, saídas e locais (`ProcessRegion`, `:469`); coleta os itens já colocados (`ApplyOrStoreItem`); repete até `logicUpdated == false`.
  - `CheckBeatable` (`:605`) é a mesma busca, que para quando encontra o item `RG_TRIFORCE`.
  - A condição de vitória é um **item** `RG_TRIFORCE` colocado em `RC_GANON` ou em `RC_WINCON` (`item_pool.cpp:350-359`).
- **Esferas:** `GeneratePlaythrough` (`fill.cpp:577`). Os itens achados em uma passada só são aplicados no início da próxima (`InitLoop`, `fill.hpp:46-54`), e isso define as esferas. Ativar um evento reinicia a esfera (`resetSphere`).
- **Poda:** `PareDownPlaythrough` (`:723`) remove cada item de trás para frente e testa `IsBeatableWithout` (`:305`). Só ficam os itens necessários.
  - Tokens, bombchus e itens de loja são tratados como "classe": `ignore` ignora todos os do mesmo tipo.
  - `GetMaxGSCount` (`:232`) corta tokens inúteis.
- **WotH:** `CalculateWotH` (`:772`) marca os itens cuja remoção torna a seed não zerável.
- **"Beatable only" vs "all locations":** o default é só zerável. Com ACR desligado, o resto da progressão é jogado ao acaso assim que dá para zerar (`:946`), então alguns locais podem ficar inalcançáveis. Com `RSK_ALL_CHECKS_REACHABLE` (`settings.cpp:1478`), todo item de progressão passa pelo AssumedFill. A validação explícita de "todos os locais alcançáveis com todos os itens" existe para ER (`ValidateEntrances`, `fill.cpp:623-669`, usado em `entrance.cpp:873`).
- **Chaves pequenas:** a lógica é só `contagem >= N` (`logic.cpp:1954`). O "pior caso" é **codificado à mão nas condições das portas**:
  - Cada porta exige o número de chaves que garante abri-la em qualquer ordem de gasto. Exemplo: Fire Temple em `R/location_access/dungeons/fire_temple.cpp:24-366`.
  - O caso especial da chave em loop usa `IsFireLoopLocked()` (`logic.cpp:2957`): se a chave pode estar fora da dungeon, exige 8 chaves; em Own Dungeon, não exige.
  - Spirit tem uma estrutura própria com mínimos por idade e por direção (`SpiritLogicData`, `location_access.h:112-136`).
  - Como a contagem só cresce, consumir chaves nunca faz o item "sumir" na lógica.
- **Munição e carteira:** recargas compráveis entram como eventos (`LOGIC_BUY_*`); bombchu exige fonte de recarga (`logic.cpp:55-59`). Lojas e scrubs exigem `GetCheckPrice() <= GetWalletCapacity()` (`location_access.cpp:102-128`, ex. `dungeons/dodongos_cavern.cpp:34`). Magia é assumida recarregável (`logic.cpp:548-549`).
- **Ganon:**
  - Ponte: `CanBuildRainbowBridge` (`logic.cpp:1846`), com variantes vanilla, pedras, medalhões, recompensas, dungeons, tokens, triforce e Greg.
  - Chave do chefe do Ganon: `CanTriggerGBK` (`:1871`).
  - Alma de Ganon e wincon: `:1898` e `:1926`.
  - Trials: `RSK_GANONS_TRIALS` (`settings.cpp:266`), com hints próprias (`hints.cpp:471`).
- **Itens iniciais:** só entram na lógica depois de validar uma região inicial alcançável (`ValidateOtherEntrance`, `fill.cpp:112-138`). Em ER, o fill também exige que exista acesso a Kokiri ou Kakariko e passagem de tempo (`:151-173`).

## 5. Categorias de check e settings principais (defaults)

**Tipos de check** (`R/randomizerEnums/RandomizerMiscEnums.h:96-141`):
- Padrão: baús, NPCs, PoH, etc.
- Skulltula tokens, vacas, troca adulta, rupias das rãs.
- Mapa, bússola, chaves (incluindo Gerudo), chave do chefe e chave do Ganon.
- Lojas, scrubs, mercadores, jogo dos baús, Link's Pocket.
- Locais de música, recompensas de chefe, ocarinas.
- Pots, crates, rochas, pedregulhos, árvores, arbustos, grama, "wonder items".
- Colmeias, peixes, freestanding (rupias e corações), silver rupees.
- Fadas (fonte, pedra, feijão, música, borboleta).
- Placas, mendigo, estalactites, gelo vermelho.

Settings (linha do `OPT_*` em `R/settings.cpp`):

| Setting | Default |
|---|---|
| Músicas (`:598`) | Song Locations |
| Tokens (`:643`) | Off |
| Shopsanity (`:599`) | Off |
| Scrubs (`:644`) | Off |
| Recompensas de dungeon (`:556`) | End of Dungeons |
| Small keys (`:1112`) | Own Dungeon |
| Boss keys (`:1117`) | Own Dungeon |
| Mapas e bússolas (`:1111`) | Own Dungeon |
| Chave do Ganon (`:1118`) | Vanilla |
| Chaves de Gerudo (`:1113`) | Vanilla |
| Freestanding, Pots, Crates, Grass (`:1080/863/865/864`) | Off |
| Ponte (`:201`) | Vanilla |
| Floresta (`:185`) | Closed |
| Idade inicial (`:278`) | Child |
| Item pool (`:1405`) | Balanced |
| Link's Pocket (`:587`) | Dungeon Reward |
| Wincon (`:1228`) | Defeat Ganon |
| Trials (`:266`) | Set Number |
| Open Chest (`:858`) | Off |

Também são toggles: vacas, colmeias, Kokiri Sword, Master Sword, ocarinas, troca adulta, carteira de criança, nadar, escalar, vara de pesca e 100 GS.

O tamanho do pool de corações segue o item pool (`item_pool.cpp:1043-1078`). Depois o pool é completado com ice traps e junk até ter exatamente o número de locais (`:1080-1143`).

## 6. Spoiler log, playthrough e hints

O JSON (`spoiler_log.cpp:292-348`) tem as chaves:
- `version`, `seed`, `finalSeed`, `file_hash`.
- `settings`, `excludedLocations`, `enabledTricks`, `masterQuestDungeons`, `requiredTrials`, `SelectedStartingAge`.
- `playthrough`: `"sphere 00"`, `"sphere 01"`, … cada uma com `{nome do local: item}` (`:221-232`). Contém **só os itens podados** (necessários).
- Hints, `entrances` / `entrancesMap` (ER).
- `locations`: `{nome: item}` ou `{nome: {item, price, model, trickName}}`.

Esse arquivo é relido pelo jogo para jogar a seed.

Hints (`hints.cpp`):
- Distribuições com pesos (`:153-210`): WotH, Foolish/barren, Song, Overworld, Dungeon, Named Item, Random, com cópias e limites por dungeon.
- `DistributeAndPlaceHints` (`:536`) sorteia por peso entre locais com flag "hintable" (só os que passaram pelo fill com lógica).
- Barren (`fill.cpp:802`) = área sem item major e sem WotH.
- Há também hints estáticas: altar, Ganondorf, warp songs, trials.

## 7. Subconjunto mínimo para outro engine (só baús + itens freestanding + save)

O essencial, mesmo para um rando de "baús + peças de coração":

1. **Tabela de checks**: id estável → (cena/stage, identificador do ator no arquivo de stage, item vanilla, tipo, área, dungeon). É o equivalente a `location_list.cpp`. É ela que diz *onde* escrever o item.
2. **Tabela de itens**: id → nome, tipo (major, progressão, chave, junk), "é progressão?", efeito lógico.
3. **Grafo de regiões**: regiões com saídas condicionais, locais condicionais e eventos. Sem isso não há garantia nenhuma. Dá para começar grosseiro (uma região por área de mapa) e refinar.
4. **Estado lógico** (inventário simulado) + helpers `has/can_use` com **restrição de idade** e **viagem no tempo** (Door of Time / Master Sword). OoT sem idade na lógica gera seeds impossíveis.
5. **Busca de ponto fixo** (reachability) e **AssumedFill** com retries; FastFill para junk.
6. **Chaves pequenas**: se baús de dungeon entram no pool, as chaves também entram. Ou se mantêm as chaves vanilla e só se embaralha o resto, que é o mais simples. Se embaralhar, precisa da contagem de pior caso por porta.
7. **Condição de vitória** como item virtual, e a checagem `CheckBeatable` no final.
8. **Itens progressivos** (hookshot→longshot, força, escala, carteira, espada): o engine precisa entregar "o próximo nível". Isso depende do runtime do jogo, não do fill.
9. **Spoiler log** com esferas: fundamental para depurar a lógica.

Pode ficar de fora no MVP: ER, shopsanity, scrubs, pots/crates/grama, hints, ice traps, MQ, tricks, triforce hunt, habilidades embaralháveis.

## Recomendações para o nosso randomizer

1. **Mesma arquitetura, em Python puro:**
   - `checks.yaml` (tabela estática gerada a partir dos stages/BYML que já decodificamos).
   - `items.yaml`.
   - `logic/*.py`: regiões como dicts, condições como funções Python ou mini-DSL de strings avaliadas contra um objeto `State`, como o SoH faz com lambdas.
2. **Estado com 4 bits por região** (criança/adulto × dia/noite) só se o remake tiver mecânica dia/noite relevante. Senão, 2 bits (criança/adulto) já cobrem o essencial. Implementar a propagação de viagem no tempo pela "porta do tempo".
3. **Fill:**
   - Seed em string → hash junto com as settings serializadas → `random.Random(hash)` único.
   - Ordem: excluídos → chaves e itens de dungeon (restritos) → progressão (AssumedFill, retries locais 10 / globais 5) → junk (FastFill).
   - Começar **com ACR ligado** (todos os locais alcançáveis), que é mais seguro para um jogo novo.
4. **Chaves no MVP:** manter small keys e boss keys **vanilla**, e embaralhar só os outros conteúdos de baú e as PoH/HC freestanding. Elimina toda a lógica de pior caso de portas. Depois implementar "own dungeon" com condições `keys >= N` escritas por porta.
5. **Aplicação:**
   - Como só podemos editar o item dentro do baú e o ator freestanding no stage, cada check precisa de um **identificador de ator reproduzível** (stage + índice/hash do ator + flag de coleta) e do **ID de item do remake** para o novo conteúdo.
   - Itens que o engine não entrega como freestanding (ex.: músicas, medalhões) devem ficar **fora do pool** desses locais (pool restrito por tipo de local, como o SoH faz com listas de locais permitidos).
   - Itens progressivos: verificar se o remake já faz upgrade automático. Se não fizer, colocar só itens não progressivos ou exigir ordem fixa.
6. **Save file:** usar para itens iniciais e flags de "mundo aberto" (floresta aberta, Door of Time aberta, Kakariko), como o `savefile.cpp` do SoH. Isso reduz muito a lógica obrigatória.
7. **Validação e depuração:**
   - Gerar spoiler JSON com `playthrough` em esferas podadas (algoritmo `PareDown` = remover item, testar se ainda zera).
   - Ter um modo "vanilla fill" que coloca tudo no lugar original e confere se a lógica considera o jogo zerável. É o melhor teste da própria lógica.
8. **Não portar no começo:** hints, ER, MQ, tricks, shopsanity. Adicionar "tricks" depois como flags booleanas consultadas nas condições.
