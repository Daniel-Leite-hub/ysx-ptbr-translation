# Roteiro de apresentação — Ys X PT-BR Translation Studio

Tempo sugerido: 8 a 12 minutos. O objetivo é demonstrar raciocínio de engenharia, evolução orientada por problemas e cuidado com dados, não apenas mostrar uma interface pronta.

## 1. Abertura — 30 segundos

> “Este projeto é uma ferramenta de engenharia de localização para Ys X: Proud Nordics. Eu desenvolvi um fluxo completo para localizar textos em arquivos proprietários, extrair, traduzir, revisar, validar e gerar um mod instalável de forma reversível. O projeto combina engenharia reversa de formatos, persistência, integração com APIs, interface, testes e empacotamento Windows.”

Apresente rapidamente os números:

- 43.588 segmentos catalogados;
- 216 scripts de cenário analisados;
- 39 tabelas de dados localizáveis;
- 43.588 traduções automáticas salvas;
- 22 testes automatizados;
- 39/39 tabelas com round-trip exato;
- revisão humana e QA integral dentro do jogo ainda em andamento.

## 2. Problema original — 1 minuto

Explique que os textos não estavam em arquivos simples:

- o jogo usa arquivos P3A;
- diálogos ficam em scripts `.dat` estruturados;
- itens, menus, missões e registros ficam em tabelas `.tbl`;
- tags e comandos misturam-se ao texto;
- traduções maiores podem prejudicar o layout;
- o jogo precisa renderizar caracteres como `ç`, `ã` e `é`;
- um tradutor precisa distinguir rascunho automático de texto revisado.

Frase sugerida:

> “O desafio não era chamar uma API de tradução. Era garantir que o texto pudesse sair e voltar aos arquivos do jogo sem perder estrutura, comandos ou rastreabilidade.”

## 3. Descoberta e extração — 1 minuto e 30 segundos

Mostre a arquitetura de fontes:

```text
script.p3a -> script_eng/scena/*.dat -> Ingert -> *.ing
table_eng/*.tbl -> KuroTools + schemas -> JSON estruturado
```

Explique a evolução:

1. A primeira versão encontrou 23.848 textos nos scripts.
2. Testes no jogo mostraram descrições ausentes.
3. A investigação identificou `table_eng` como segunda fonte.
4. Uma comparação automática entre tabelas inglesas e espanholas separou conteúdo localizável de IDs técnicos.
5. O catálogo chegou a 43.588 registros.

Destaque o método: a versão espanhola funcionou como evidência de quais campos eram realmente localizados, evitando traduzir nomes de assets, funções e chaves internas.

## 4. Modelo de dados e segurança — 1 minuto

Apresente os quatro estados persistentes:

```text
Original em inglês
        ↓
Tradução automática
        ↓
Validação técnica
        ↓
Texto final revisado
```

Explique o SQLite:

- uma linha por segmento e localizador estrutural;
- tradução e revisão em campos separados;
- histórico de edições;
- WAL, `synchronous=FULL` e checkpoint;
- backups consistentes antes de migrações e builds;
- revisão tem prioridade; sem revisão, usa-se a tradução automática.

## 5. Tradução automática — 1 minuto

DeepL:

- endpoints separados para Free e Pro;
- XML v2 e tags ignoradas;
- glossário por ID;
- erros fatais 400/401/403/404 não são mascarados como progresso.

Problema encontrado: o DeepL retornava 404 porque um endpoint de outro serviço contaminava a rota. Solução: separar completamente a escolha do provedor e usar os hosts oficiais.

## 6. Validação de texto e layout — 1 minuto

Explique:

- largura calculada sem contar tags;
- caracteres wide recebem largura 2;
- quebra somente entre palavras;
- limite de 72 colunas;
- linha 3 só existe quando a linha 2 transborda;
- palavras longas não são cortadas silenciosamente;
- modo visual e modo estrito por bytes;
- proteção de tags e formatos `%d`, `%.1f`, `%%`.

Problema encontrado: quebras existentes eram preservadas mesmo quando prematuras, produzindo linhas 2 e 3 desorganizadas. Solução: recompor o diálogo e aplicar a quebra sequencial novamente.

## 7. Interface e experiência do usuário — 1 minuto

Demonstre:

- lista pesquisável com status;
- original copiável;
- tradução automática e revisão lado a lado;
- botão de salvar trecho;
- validação individual;
- marcar como revisada;
- histórico da linha;
- dashboard de progresso;
- tela de API e tela de QA separadas.

Problemas encontrados:

- botões de validação pouco visíveis;
- salvamento a cada tecla;
- erros que permaneciam após a correção;
- carregamento infinito causado por um `MutationObserver` recursivo.

Soluções:

- reorganização inspirada no fluxo do Refrain Studio;
- salvamento ao concluir a edição;
- revalidação independente do conteúdo ter mudado;
- atualização idempotente do DOM e desconexão temporária do observer.

## 8. Reinserção e aplicador — 1 minuto

Explique o build:

1. usa revisão ou tradução automática como fallback;
2. substitui expressões nos scripts;
3. recompila tabelas com seus localizadores;
4. recompila e decompila scripts como verificação estrutural;
5. cria `zzz_ysx_ptbr.p3a`;
6. executa `p3a_tool verify`.

Apresente o aplicador separado:

- valida a instalação original;
- copia somente para a pasta `mods`;
- preserva versão anterior;
- usa troca atômica;
- compara SHA-256;
- gera log auditável.

## 9. Qualidade, limites e ética — 45 segundos

> “Eu separo validação técnica de validação editorial. O pipeline e os arquivos foram verificados, mas isso não significa que todas as frases estejam revisadas ou que todas as telas tenham sido inspecionadas dentro do jogo.”

Deixe claro:

- 100% possui tradução automática salva;
- revisão humana está em andamento;
- testes não substituem QA visual no jogo;
- o repositório público não inclui executável do jogo, arquivos originais, textos extraídos, chaves ou ferramentas proprietárias.

## 10. Encerramento — 30 segundos

> “Este projeto demonstra competências de engenharia de software em análise de requisitos, modelagem de dados, integração de serviços, programação defensiva, testes, documentação, versionamento e entrega para usuário final. A principal aprendizagem foi transformar uma sequência de problemas reais em uma arquitetura reutilizável e verificável.”

## Perguntas que um recrutador pode fazer

### Por que SQLite?

Porque o trabalho precisa sobreviver a interrupções, suporta consultas e filtros eficientes, oferece transações e permite backup consistente sem introduzir um servidor externo.

### Como você evita que a API quebre comandos do jogo?

Tags e placeholders são substituídos por tokens protegidos antes da requisição. Depois da resposta, eles são restaurados e a assinatura estrutural é comparada à original.

### Como sabe que uma tabela recompilada é válida?

O teste de round-trip extrai e recompila sem alterações e compara o arquivo inteiro. As 39 tabelas selecionadas produziram o mesmo tamanho e SHA-256 dos originais.

### O projeto está concluído?

A engenharia do pipeline está funcional e testada. A tradução automática cobre o catálogo, mas a revisão humana e a inspeção integral dentro do jogo continuam em andamento.

### O que você faria depois?

- testes automatizados de integração com amostras sintéticas maiores;
- mecanismo de atualização incremental de schemas;
- filtros editoriais por personagem/contexto;
- relatório de QA por cena;
- capturas de antes/depois autorizadas para o portfólio.
