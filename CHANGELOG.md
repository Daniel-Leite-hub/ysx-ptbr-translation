# Histórico de versões

Este arquivo registra alterações funcionais, decisões técnicas, validações e pendências. Ele deve ser atualizado em toda nova versão distribuída.

## 2.3.5 — catálogo de falas de combate — 25/10/2026

- Incluída a leitura dos textos de combate presentes em cinco scripts de animação de `script_eng/ani`, mantendo os offsets e separando essa identidade dos scripts de cena.
- A sincronização preserva traduções existentes e só reaproveita tradução idêntica quando há uma única opção; a revisão continua explícita por linha.
- A reconstrução mantém esses recursos no caminho `script_eng/ani` do pacote, em vez de colocá-los junto aos scripts de cena.
- Foram catalogadas 74 falas; 20 estavam revisadas e 54 permaneciam como rascunhos. O banco privado não é distribuído.
- A compilação estrutural e a reinserção dos 74 textos foram conferidas no pacote local. A inspeção visual dessas falas no jogo continua pendente.
- Esta atualização documenta o estado local; não significa publicação de uma Release nem envio ao GitHub.

## Campos internos da pesquisa marinha — 20/10/2026

- Extração de `profile[].type` e `imressions[].text` sem renumerar os campos históricos da tabela.
- Localizadores estruturais e campos de uma linha para o painel. Acrescentados 105 registros ao catálogo privado.
- Dois testes sintéticos para extração, identidade e formatação; dados reais não são incluídos no repositório.

## Compartilhamento — 09/10/2026 (executável 2.3.4 atualizado)

- Seção Compartilhar tradução na tela de validação: ZIP para copiar na pasta do jogo e instalador EXE autossuficiente.
- A geração pelo Studio recompila o estado salvo antes de empacotar, bloqueando textos inválidos.
- ZIP contém somente mod, manifesto e guia de backup/remoção; as fontes nativas já suportam PT-BR.
- EXE incorpora o patch e confere SHA-256 do executável, script original e pacote. Versão incompatível é bloqueada.
- Backup conferido, substituição atômica, registro da instalação, log e restauração do estado anterior. Mod alterado externamente não é sobrescrito na restauração.
- Reinstalação mantém o primeiro estado anterior; restauração sem mod anterior retira apenas a tradução e mantém cópia recuperável.
- 44 testes Python e testes do motor C# em pastas simuladas. Nenhuma execução de cenas do jogo foi realizada nesta atualização.

## Cinemáticas — 07/10/2026 (executável 2.3.4 atualizado)

- Corrigida lacuna de cobertura: as legendas Maya Scene não constavam no catálogo nem no P3A.
- Varridos 41 arquivos; adicionadas e localizadas 129 falas (150 segmentos) em 16 arquivos.
- Incluídos 258 contextos oficiais ES/JA, alinhados por caminho JSON, voz, falante e tempo.
- Extração, sincronização e exportação passam a contemplar `maya_scene_eng`; busca `tag:cinematicas`.
- Preservados número de segmentos, controles de pausa, áudio, animações e tempos. IDs de voz repetidos não são usados como chave única.
- Backup SQLite anterior à migração e backup do mod anterior. Banco e pacote portátil sincronizados.
- 41 testes automatizados. Integridade e reinserção são verificações estruturais; validação visual das cenas ainda necessária.

## Dados de tradução — aprovação final de 05/10/2026

- Aplicadas 6.535 propostas adicionais dos relatórios editoriais; 251 já estavam aplicadas, totalizando 6.786 propostas aprovadas.
- Preservados original, tradução automática, metadados e histórico; backup consistente pela API SQLite antes da escrita.
- Aprovação das ambiguidades registrada; quando não existe alternativa concreta, preservado o texto atual sem inventar referências ou gênero.
- Entrega privada e mod local atualizados somente após conferência da reinserção e integridade do P3A.
- Organização e limpeza documentadas em `docs/ORGANIZACAO.md`; versão do EXE continua 2.3.4, pois esta atualização é editorial.
- Teste visual completo no jogo continua necessário; não confundir instalação com validação visual.

## 2.3.4 — 12/09/2026

- Incluídos falante, gênero e confiança no catálogo, com origem rastreável no roteiro/perfil.
- Adicionado o botão **Mapear falantes** e a exibição do contexto de falante no Editor.
- Corrigidas 66 concordâncias seguras de primeira pessoa: 56 da Karja e 10 da Lila.

## 2.3.3 — 12/09/2026

- Padronizados `ruivo`, `embarcação` e `navio-almirante` no catálogo e no glossário de exemplo.
- Adicionado utilitário reprodutível para simular, validar, criar backup e aplicar a padronização.
- Reescritos os textos longos afetados para preservar os limites de layout.

## 2.3.2 — 11/09/2026

- Escolhas agora possuem limite próprio de 67 colunas e uma linha; o Studio não reflowa uma opção para outro balão.
- Mapeadas e revisadas as duas escolhas que ultrapassavam o limite visual: IDs 21150 e 43627.
- Adicionado o relatório `docs/REVISAO_BALOES_ESCOLHA.md` e teste de regressão para o balão de escolha.

## 2.3.1 — 10/09/2026

### Adicionado

- Mapeamento de 36 tags editoriais para diálogos, vozes, escolhas, menus, itens, habilidades, descrições, tutoriais, missões, perfis e demais categorias encontradas.
- Busca por uma ou várias expressões `tag:categoria`, combinável com texto livre e arquivo; singular e acentos são normalizados.
- Painel expansível de atalhos de categoria abaixo da busca do Editor.
- Coluna `tags_busca` na exportação CSV e relatório reproduzível `tools/audit_content_tags.py`.
- Documento `docs/MAPA_TAGS.md` com origens, exemplos e contagens do catálogo atual.

### Corrigido no catálogo

- Cinco traduções automáticas de ajuda/bestiário foram condensadas de quatro para até três linhas, respeitando 72 colunas.
- A notificação de nível de almoço do Sandras teve a sequência original de tags restaurada.
- As seis linhas foram revalidadas individualmente; o catálogo voltou a zero erros sem apagar traduções ou revisões.

## 2.3.0 — 10/09/2026

### Corrigido

- Espaços HTML `&#x20;`, `&#32;` e `&nbsp;` e quebras meramente visuais são convertidos em espaços comuns antes do envio ao DeepL. O trecho `in 0013` agora chega à API como uma única frase contínua.
- A extração de scripts passou a reconhecer avisos, confirmações, vozes ativas, obtenção de itens, lojas e menus emitidos por comandos além de `system[5,11]` e `M_SELECTION_*`.
- Agrupamento conservador impede que parâmetros dinâmicos, IDs e variáveis sejam incorporados ou apagados durante a recompilação.

### Adicionado

- 1.332 ocorrências visíveis que faltavam no catálogo; a cobertura verificada agora contém 44.950 entradas e zero ocorrências ausentes entre os comandos suportados.
- Comando **Sincronizar textos brutos** para repetir a auditoria incremental com backup.

### Estado dos dados

- Todas as 43.704 traduções automáticas foram limpas a pedido do tradutor para iniciar uma nova rodada.
- A única revisão humana foi preservada, assim como o histórico de edições e o backup anterior ao reset.
- Estado após a limpeza: 0 traduções automáticas, 1 revisão e 44.949 entradas pendentes.

## 2.2.2 — 10/09/2026

### Adicionado

- Campo editável **Contexto narrativo do DeepL**, preenchido por padrão com orientação para fantasia/RPG, diálogos polidos e adequação de registro ao contexto.

### Alterado

- Antes de cada envio ao DeepL, quebras visuais são unidas e palavras hifenizadas entre linhas são recompostas. A tradução recebe o enunciado contínuo; a quebra de até 72 colunas é aplicada somente à resposta.
- Requisições DeepL agora enviam `context`, `split_sentences=1` e `preserve_formatting=false`, mantendo as tags/comandos em XML protegido.

## 2.2.1 — 10/09/2026

### Corrigido

- Extração das escolhas `M_SELECTION_CHR_NO_CURSOR` e `M_SELECTION_CHR_ENABLE_CANCEL`, que podiam permanecer em inglês mesmo quando a mesma frase de legenda já estava traduzida.
- O script `tools/build_release.py` agora encontra o módulo local quando chamado diretamente, conforme a documentação.

### Adicionado

- Botão **Procurar escolhas ausentes** em **Validação e pacote**. A sincronização cria backup, preserva edições e só reaproveita tradução quando há uma única correspondência exata; a marca de revisão humana não é copiada automaticamente.
- 30 ocorrências de escolhas foram adicionadas ao catálogo existente; 2 traduções idênticas foram reaproveitadas para `mp_s0001.ing`.

## 2.2.0 — 07/09/2026

### Adicionado

- Auditoria comparativa das 90 tabelas `table_eng` e `table_spa`.
- Extração de 39 tabelas com conteúdo confirmado como visível ao jogador.
- Categorias para diálogos/vozes, itens, interface/ajuda, missões/jornal, mapas, habilidades e bestiário.
- 15.868 novos registros; catálogo total ampliado para 43.588 entradas.
- Recompilação de tabelas pelo KuroTools e inclusão de `table_eng` no P3A.
- Proteção de marcadores `printf`, como `%d`, `%.1f` e `%%`.
- Aplicador Windows separado, com instalação atômica, backup, SHA-256 e log.
- Pacote portátil privado e estrutura pública sanitizada para portfólio/GitHub.

### Alterado

- Diálogos vindos de scripts ou tabelas usam o mesmo reflow sequencial de 72 colunas.
- O executável principal passou ao formato de pasta portátil para evitar falhas de extração temporária de DLL do modo one-file.

### Validado

- 39/39 tabelas recompiladas de forma byte a byte idêntica quando não há edições.
- P3A final verificado pelo `p3a_tool verify`.
- 22 testes automatizados aprovados.
- `PRAGMA integrity_check` do projeto retornou `ok`.
- 43.588 traduções automáticas salvas e zero erros técnicos no catálogo.

### Pendente

- Revisão humana editorial: apenas uma entrada está marcada como revisada.
- Validação visual completa dentro do jogo, em diferentes menus e resoluções.
- `t_tbox.tbl` não foi incluída: o schema disponível não decodificou o arquivo e a comparação de idiomas não apresentou evidência de texto visível.

## 2.1.0 — 07/09/2026

- Inclusão inicial de `t_item.tbl`, `t_character_lib.tbl` e `t_adventure_log.tbl`.
- 3.872 entradas de itens e jornal adicionadas.
- Reflow de quebras prematuras: a terceira linha só é criada quando a segunda transborda.
- Round-trip e teste de acentos realizados nas três tabelas.

## 2.0.5 — 06/09/2026

- Correção do observador de mutações que podia manter a interface em carregamento infinito.
- Atualização idempotente do indicador de texto efetivo.

## 2.0.4 — 06/09/2026

- Tradução automática passou a ser o texto usado no build enquanto a revisão estiver vazia.
- CSV passou a informar separadamente original, tradução automática, revisão e texto efetivo.

## 2.0.3 — 06/09/2026

- Original tornou-se copiável.
- Remoção do salvamento a cada tecla; gravação ocorre ao concluir o trecho ou mudar de linha.
- Validação individual passou a limpar erros antigos depois da correção.

## 2.0.2 — 06/09/2026

- Quebra automática por palavra no limite visual de 72 colunas.
- Palavras maiores que o limite permanecem inteiras e são sinalizadas.

## 2.0.1 — 06/09/2026

- Correção do erro HTTP 404 no DeepL.
- Separação explícita entre `api-free.deepl.com` e `api.deepl.com`.

## 2.0.0 — 05/09/2026

- Interface WebView2 reconstruída com base no fluxo visual do Refrain Studio.
- Navegação lateral, painel de métricas, editor dividido e telas próprias para tradução e QA.

## 1.3.0 — 05/09/2026

- Salvamento explícito, histórico de até 50 versões por linha e backups SQLite.
- Botões visíveis para validar uma linha e marcar como revisada.

## 1.0.0 — 31/08/2026

- Extração inicial de scripts PH3/P3A com Ingert.
- Projeto SQLite com original, tradução, validação e revisão.
- Integração inicial com DeepL.

## Procedimento para a próxima versão

1. Criar backup consistente do `.ysxproj`.
2. Atualizar schemas/extratores sem apagar traduções existentes.
3. Executar os testes automatizados.
4. Revalidar todo o catálogo e executar `PRAGMA integrity_check`.
5. Fazer round-trip sem alterações e comparar hashes.
6. Gerar o P3A e executar `p3a_tool verify`.
7. Testar a inicialização dos dois executáveis.
8. Atualizar este changelog, o manifesto SHA-256 e o status editorial.
9. Fazer QA dentro do jogo antes de declarar uma tradução final.
