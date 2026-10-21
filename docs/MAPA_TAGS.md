# Mapa de tags do catálogo

Atualizado em 10/09/2026 para o catálogo de 44.950 textos. As categorias são editoriais e não alteram tags, comandos ou arquivos do jogo. Um registro pode receber várias tags.

## Como pesquisar

- Digite `tag:itens`, `tag:habilidades`, `tag:tutoriais` etc. na busca do Editor.
- Acentos e singular são aceitos: `tag:missão`, `tag:descrição` e `tag:item` são normalizados.
- Combine tags para exigir todas: `tag:habilidades tag:descricoes`.
- Combine texto e tags: `Adol tag:dialogos` ou `HP tag:itens tag:descricoes`.
- Abra **Tags de categoria** abaixo da busca para usar os atalhos visuais.

## Categorias encontradas

| Tag | Conteúdo mapeado | Ocorrências |
|---|---|---:|
| `tag:dialogos` | Diálogos de cena, falas em tabelas e vozes | 29.404 |
| `tag:vozes` | Vozes ativas, falas de navio e banco de diálogo | 7.537 |
| `tag:escolhas` | Escolhas do jogador | 2.163 |
| `tag:menus` | Menus, escolhas, configurações, lojas e textos gerais de interface | 4.758 |
| `tag:interface` | Interface, ajuda, tutoriais e avisos de sistema | 4.247 |
| `tag:sistema` | Mensagens de sistema e tabelas gerais do jogo | 3.333 |
| `tag:notificacoes` | Alertas, confirmações, obtenção de itens e avisos | 874 |
| `tag:itens` | Nomes e descrições de itens, DLC e itens de Time Attack | 3.748 |
| `tag:habilidades` | Habilidades, bônus de vínculo e ações de Mana | 493 |
| `tag:descricoes` | Campos de descrição, detalhes, observações, perfis e tutoriais | 4.237 |
| `tag:nomes` | Nomes, títulos e cabeçalhos identificados | 3.148 |
| `tag:tutoriais` | Ajuda e dicas | 1.667 |
| `tag:missoes` | Missões, quests, eventos e recaptura de ilhas | 1.976 |
| `tag:eventos` | Eventos, tópicos e registros da aventura | 1.666 |
| `tag:diario` | Diário, jornal, perfis, missões, cartas, runas e tópicos | 2.419 |
| `tag:perfis` | Perfis da biblioteca de personagens | 273 |
| `tag:personagens` | Perfis e tabela de nomes | 829 |
| `tag:bestiario` | Monstros e pesquisas/observações | 233 |
| `tag:mapas` | Áreas, ilhas, viagem rápida, pontos e tesouros | 555 |
| `tag:viagem-rapida` | Destinos de viagem rápida | 163 |
| `tag:tesouros` | Mapas do tesouro | 17 |
| `tag:lojas` | Diálogos, menus e tabelas de loja | 1.056 |
| `tag:navio` | Conversas e planos de melhoria do navio | 1.200 |
| `tag:melhorias` | Melhorias do navio e bônus de vínculo | 989 |
| `tag:conquistas` | Nomes e descrições de conquistas | 110 |
| `tag:dlc` | Nomes e descrições de DLC | 225 |
| `tag:minijogos` | Arena, pesca, Mana Ride e Time Attack | 293 |
| `tag:arena` | Estágios da arena | 69 |
| `tag:pesca` | Peixes e descrições relacionadas | 81 |
| `tag:mana-ride` | Estágios e abas do Mana Ride | 19 |
| `tag:cartas` | Cartas de Fugil | 52 |
| `tag:runas` | Pedras rúnicas | 51 |
| `tag:configuracoes` | Configurações e controles | 523 |
| `tag:controles` | Configuração de teclas/controles | 80 |
| `tag:culinaria` | Refeições e seus efeitos | 21 |
| `tag:recaptura` | Missões e mensagens de recaptura de ilhas | 193 |

As contagens se sobrepõem porque um texto pode ter mais de uma tag.

## Origem das tags

| Origem | Tags principais |
|---|---|
| Scripts `system[5,11]` | `dialogos` |
| Scripts `system[5,22]` | `dialogos`, `vozes` |
| Scripts `M_SELECTION_*` | `escolhas`, `menus` |
| Scripts de sistema/alerta | `sistema`, `interface`, `notificacoes` |
| `t_item.tbl` | `itens`, mais `nomes` ou `descricoes` conforme o campo |
| `t_skill.tbl`, `t_skill_tree_link_bonus.tbl`, `t_mana_action_level_up.tbl` | `habilidades`, mais `nomes`, `descricoes` ou `melhorias` |
| `t_help.tbl`, `t_tips.tbl` | `tutoriais`, `interface`, `descricoes` |
| `t_quest.tbl`, `t_mission.tbl` | `missoes`, `diario` |
| `t_character_lib.tbl` | `perfis`, `personagens`, `diario`, `descricoes` |
| `t_adventure_log.tbl`, `t_event.tbl`, `t_topic.tbl` | `diario`, `eventos`, `missoes` |
| `t_monster_lib.tbl`, `t_research.tbl` | `bestiario`, `descricoes` |
| Tabelas de mapa | `mapas`, `viagem-rapida` ou `tesouros` |
| Tabelas gerais | Tags específicas como `lojas`, `navio`, `conquistas`, `dlc` e `minijogos` |

Para recontar o catálogo após futuras extrações:

```powershell
python tools/audit_content_tags.py YsX_PTBR_Projeto.ysxproj
```
