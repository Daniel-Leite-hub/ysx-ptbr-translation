# Estudo técnico — construção do Ys X PT-BR Translation Studio

## 1. Objetivo e requisitos

O projeto nasceu da necessidade de localizar para português brasileiro um jogo cujos textos não estavam disponíveis em arquivos editáveis comuns. A solução precisava cobrir o ciclo inteiro:

1. localizar todas as fontes de texto;
2. extrair mantendo um vínculo reversível com o arquivo de origem;
3. armazenar original, tradução automática e revisão separadamente;
4. integrar DeepL de modo seguro;
5. proteger tags e comandos;
6. validar tamanho e layout;
7. recompilar os formatos;
8. produzir um mod verificável;
9. oferecer uma interface Windows e um aplicador simples;
10. manter backups, histórico e documentação.

Um princípio guiou o desenvolvimento: uma interface abrir ou uma API responder não prova que o jogo foi traduzido. Cada camada deve possuir sua própria evidência.

## 2. Reconhecimento do formato

### 2.1 Contêiner P3A

O jogo usa pacotes P3A da PH3. A ferramenta `p3a_tool.exe` disponível na instalação permite listar, extrair, criar e verificar esses arquivos. O pipeline não modifica diretamente os grandes pacotes originais. Ele produz um arquivo com nome de alta prioridade, `zzz_ysx_ptbr.p3a`, instalado na pasta `mods`.

Essa estratégia possui vantagens:

- preserva a instalação original;
- permite remover o mod sem restaurar gigabytes de dados;
- reduz o tamanho da distribuição;
- facilita comparar versões;
- permite backup independente do mod anterior.

### 2.2 Scripts de cenário

Os diálogos principais estão em `script_eng/scena/*.dat`. Esses arquivos contêm bytecode e expressões estruturadas, não uma lista linear de strings. O Ingert foi escolhido porque oferece modo round-trip adequado ao formato e desempenho melhor que a alternativa avaliada para os scripts grandes.

O processo é:

```text
.dat original -> Ingert --roundtrip -> .ing editável
.ing alterado -> Ingert -> .dat recompilado
.dat recompilado -> Ingert --roundtrip -> verificação estrutural
```

O extrator procura chamadas conhecidas de mensagem e escolha, calcula o fechamento correto dos parênteses e lê literais de string com escape. Cada registro armazena:

- arquivo;
- intervalo de caracteres no `.ing`;
- texto original;
- tipo de chamada;
- contexto próximo;
- métricas e assinatura de tags.

Na reinserção, as substituições ocorrem do maior offset para o menor. Assim, alterar o tamanho de uma string posterior não invalida os offsets ainda não utilizados.

### 2.3 Tabelas TBL

A extração inicial de scripts não continha descrições de itens, fichas de personagens e vários menus. A presença de pastas paralelas `table_eng`, `table_spa`, `table_fre` e `table_ger` indicou uma camada de localização orientada a dados.

O KuroTools converte `.tbl` em JSON a partir de schemas por header. Para não traduzir nomes internos, foi feita uma auditoria comparativa:

1. converter a mesma tabela em inglês e espanhol;
2. percorrer cada `header`, registro e campo;
3. comparar strings no mesmo localizador;
4. considerar diferenças entre idiomas como evidência forte de conteúdo localizável;
5. revisar campos legíveis que permaneciam iguais;
6. excluir dados hexadecimais, caminhos, nomes de animação, IDs e funções.

O resultado foi uma lista branca de 105 campos em 39 tabelas. Cada entrada recebe um localizador JSON com seção, índice e campo. Exemplo conceitual:

```json
{"section":"ItemTableData","index":0,"field":"long_desc"}
```

Esse localizador permite reconstruir o JSON original, alterar somente o valor selecionado e recompilar a tabela.

### 2.4 Prova de round-trip

Para validar schemas e empacotamento, cada uma das 39 tabelas foi:

1. extraída para JSON;
2. recompilada sem edição;
3. comparada integralmente com o arquivo de origem.

Todas produziram igualdade byte a byte, inclusive SHA-256. Isso é mais forte que comparar apenas quantidade de registros ou verificar se o parser não lançou erro.

## 3. Persistência

O projeto usa SQLite em um arquivo `.ysxproj`. A tabela principal mantém o estado editorial e técnico de cada segmento. Os campos principais são:

- `original`: referência imutável em inglês;
- `translation`: saída automática ou rascunho;
- `reviewed`: texto final aprovado manualmente;
- métricas de bytes, largura e linhas;
- `size_ok` e `error`;
- provedor utilizado;
- contexto/localizador;
- revisão e data de atualização.

A regra de precedência é:

```python
texto_efetivo = reviewed or translation
```

Isso permite gerar builds de teste antes da revisão integral, sem copiar automaticamente o rascunho para o campo de aprovação.

### 3.1 Durabilidade

Foram configurados:

- `journal_mode=WAL`;
- `synchronous=FULL`;
- `busy_timeout`;
- transações nas gravações;
- checkpoint explícito;
- backup pela API nativa do SQLite.

O histórico registra até 50 versões por entrada. Uma gravação idêntica não cria uma versão duplicada, mas ainda recalcula a validação. Esse detalhe corrigiu registros cujo erro permanecia visível depois de o texto já estar dentro dos parâmetros.

## 4. Tradução automática

### 4.1 Preparação e proteção

Antes de enviar um texto, comandos são identificados e substituídos por tokens. A proteção cobre:

- tags entre sinais de menor/maior;
- comandos de estilo e espera;
- placeholders como `%d`, `%.1f` e `%%`;
- quebras representadas por elementos controlados.

Depois da resposta:

1. elementos auxiliares são removidos;
2. entidades HTML são restauradas;
3. tokens voltam aos valores originais;
4. a assinatura de comandos é comparada;
5. uma resposta que removeu ou duplicou controles é recusada.

### 4.3 DeepL

O erro HTTP 404 observado revelou mistura de configuração entre provedores. A correção separou os hosts:

- Free: `https://api-free.deepl.com/v2/translate`;
- Pro: `https://api.deepl.com/v2/translate`.

O DeepL usa somente os hosts oficiais do plano selecionado. São usados XML v2, tags ignoradas e glossário por ID. Erros fatais são persistidos/mostrados como falha, sem incrementar progresso falso.

### 4.4 Salvamento em lotes

Cada lote aprovado é confirmado no SQLite antes de o próximo começar. Uma interrupção perde, no máximo, o lote em andamento. Textos repetidos são agrupados para reduzir consumo de API e aplicados a todos os IDs correspondentes.

## 5. Validação visual e estrutural

### 5.1 Largura

Tags não contam para a largura. Caracteres classificados como wide pelo Unicode recebem duas colunas; os demais recebem uma. O limite padrão é 72 colunas.

O algoritmo de quebra:

1. recompõe quebras prematuras dos diálogos;
2. separa o conteúdo em palavras e espaços;
3. acumula enquanto a próxima palavra cabe;
4. move a palavra inteira para a linha seguinte quando necessário;
5. não divide uma palavra longa silenciosamente;
6. cria a terceira linha somente depois de preencher a segunda.

Descrições em tabelas podem preservar quebras semânticas existentes, mas linhas individuais acima do limite ainda são reorganizadas.

### 5.2 Políticas

O modo visual verifica:

- comandos preservados;
- ausência de byte nulo;
- largura máxima;
- quantidade de linhas.

O modo estrito adiciona a regra de que a tradução não pode possuir mais bytes UTF-8 que o original. Ele existe como ferramenta conservadora; os formatos recompilados realocam strings e, portanto, crescimento em bytes não significa automaticamente corrupção.

## 6. Interface

A interface usa HTML, CSS e JavaScript dentro do WebView2, servidos apenas por um servidor HTTP local ligado a `127.0.0.1`. Um token aleatório no fragmento da URL é exigido em toda chamada POST, reduzindo o risco de outra página controlar a API local.

O backend em Python expõe uma lista limitada de métodos. Não há execução arbitrária recebida do navegador.

### 6.1 Fluxo editorial

O editor apresenta:

1. original copiável;
2. tradução automática;
3. validação e métricas;
4. texto final revisado.

Há busca, filtros, paginação, progresso, histórico, validação individual e aprovação explícita.

### 6.2 Problemas de usabilidade resolvidos

- **Botões difíceis de encontrar:** ações foram agrupadas sob os campos.
- **Salvamento por tecla:** digitar apenas marca o trecho como pendente; salvar ocorre ao concluir ou trocar de linha.
- **Erro antigo permanecia:** a validação é recalculada mesmo sem mudança textual.
- **Carregamento infinito:** um `MutationObserver` alterava continuamente o próprio DOM observado. A solução desconecta o observer durante as melhorias e só escreve quando o valor realmente mudou.

## 7. Build e instalação

O build seleciona todo registro com tradução ou revisão válida. Scripts e tabelas seguem rotas separadas e convergem no P3A:

```text
SQLite
 ├─ scripts -> substituir .ing -> compilar .dat -> verificar
 └─ tabelas -> alterar JSON -> compilar .tbl
                         ↓
             zzz_ysx_ptbr.p3a
                         ↓
                p3a_tool verify
```

O aplicador foi escrito em C# WinForms para depender apenas do .NET Framework presente no Windows. Ele possui uma única função de usuário: aplicar a tradução.

As proteções do aplicador são:

- exige `ysx_pn.exe` e `script.p3a`;
- lê o P3A ao lado da distribuição;
- cria `mods` quando necessário;
- copia primeiro para `.tmp`;
- compara SHA-256;
- preserva o mod anterior em pasta datada;
- troca o arquivo de forma atômica;
- grava resultado e caminhos em `Aplicador_YsX.log`.

## 8. Testes e evidências

Os testes unitários cobrem:

- extração de mensagens e escolhas;
- assinatura de tags/placeholders;
- política de tamanho;
- reflow de 72 colunas;
- persistência e histórico;
- fallback da tradução enquanto a revisão está vazia;
- validação individual;
- comportamento de salvamento da interface;
- endpoints Free/Pro do DeepL;
- presença das principais fontes TBL.

Além dos testes automatizados, foram realizados:

- round-trip de scripts;
- round-trip byte a byte de 39 tabelas;
- reinserção de texto PT-BR com acentos;
- `PRAGMA integrity_check`;
- verificação do P3A;
- smoke test dos executáveis.

## 9. Empacotamento e portfólio

O modo PyInstaller de arquivo único foi abandonado porque a extração temporária de `MSVCP140.dll` falhou em um ambiente Windows. A distribuição principal usa pasta portátil (`onedir`), que inicia mais rápido e elimina essa etapa.

Existem duas entregas:

- **privada:** Studio, projeto, fontes intermediárias, P3A e aplicador;
- **pública:** código-fonte, testes e documentação, sem jogo, P3A, banco de textos, chaves ou binários proprietários.

Essa separação permite demonstrar a engenharia sem redistribuir conteúdo protegido.

## 10. Estado atual e próximos estudos

O catálogo possui 43.588 traduções automáticas salvas e zero erros técnicos. Isso não equivale a uma localização final: somente uma entrada está marcada como revisão humana.

Próximas etapas recomendadas:

1. revisão editorial por categoria;
2. glossário consistente de personagens, lugares, itens e termos náuticos;
3. QA visual em 16:9, resoluções menores e menus densos;
4. coleta de capturas e IDs de linhas problemáticas;
5. ajuste de limites por tipo de tela;
6. regressão de cenas após cada lote revisado;
7. publicação de métricas editoriais separadas das técnicas.

## 11. Aprendizados transferíveis

- confirmar todas as fontes de texto antes de chamar a extração de completa;
- comparar idiomas oficiais para descobrir campos localizáveis;
- usar lista branca em formatos estruturados;
- manter original, máquina e revisão separados;
- tratar placeholders como parte do formato, não como linguagem natural;
- salvar por lote e criar backups antes de migrações;
- provar round-trip antes de editar em massa;
- preferir instalação reversível;
- distinguir “o executável inicia”, “o arquivo recompila” e “o jogo está visualmente correto”;
- publicar no GitHub apenas o que pode ser redistribuído legalmente.
