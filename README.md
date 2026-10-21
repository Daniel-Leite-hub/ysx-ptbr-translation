# Ys X PT-BR Translation Studio

**Ferramenta Windows para extrair, traduzir, revisar e distribuir uma localização em português brasileiro de Ys X: Proud Nordics.**

Projeto independente de engenharia de localização. Reúne investigação de formatos, persistência em SQLite, integração com APIs, interface de revisão, validação de textos e instalação reversível de um mod.

Projeto independente, não oficial e sem vínculo com os titulares do jogo. Requer uma cópia legítima e compatível de **Ys X: Proud Nordics**.

## Quero apenas instalar a tradução

Na [Release mais recente](https://github.com/Daniel-Leite-hub/ysx-ptbr-translation/releases/latest) deste repositório, escolha **uma** alternativa:

| Opção | Como usar | Como desfazer |
| --- | --- | --- |
| `YsX_PTBR_Copiar_na_Pasta_do_Jogo.zip` | Feche o jogo, faça backup do mod anterior e extraia o ZIP na pasta que contém `ysx_pn.exe`, preservando a pasta `mods`. | Retire somente `mods/zzz_ysx_ptbr.p3a` e recoloque seu backup, se havia um. |
| `Instalar_YsX_PTBR.exe` | Execute, selecione a pasta do jogo e clique em **Aplicar tradução**. O patch está incorporado no EXE. | Execute o mesmo EXE e clique em **Restaurar / desfazer**. |

Use o jogo no idioma **inglês**. Não é necessário configurar APIs, instalar Python ou possuir o Studio para aplicar esses pacotes.

**Compatibilidade da entrega preparada:** versão `1.0.3_r10`. O instalador compara SHA-256 do executável e do pacote original de scripts com a instalação de referência. Outra edição/build pode ser recusada mesmo com um número de versão semelhante. O ZIP manual não executa essa conferência.

O EXE preserva o estado anterior em `mods/backup_ptbr`, mantém um registro de instalação e não restaura por cima de um mod alterado externamente. Se nunca havia mod, desfazer retira a tradução e guarda uma cópia recuperável. A restauração automática atende apenas instalações registradas pelo EXE, não a cópia manual por ZIP.

As fontes nativas auditadas já contêm os acentos do português; não são redistribuídas fontes originais. Confira o arquivo `SHA256SUMS.txt` da Release. Um EXE sem assinatura pode gerar aviso do Windows: confira origem e hash, sem desativar a proteção do sistema.

## Funcionalidades do Studio

- Extração de scripts, tabelas de interface e legendas de cinemáticas Maya Scene.
- Editor com original selecionável, tradução salva, texto revisado, histórico e validação individual.
- Prioridade de exportação: texto revisado preenchido; na ausência dele, tradução salva.
- Integração com DeepL Free/Pro, glossário e proteção de comandos e variáveis.
- Contexto editável para o DeepL; quebras apenas visuais são reunidas antes do envio, sem separar frases artificialmente.
- Limites conservadores de envio, lotes e retentativas para reduzir falhas dos provedores. Não garantem disponibilidade nem substituem as quotas da conta.
- Busca por texto e categorias, como `tag:dialogos`, `tag:itens`, `tag:missoes` e `tag:cinematicas`.
- Metadados de falantes e contexto oficial em espanhol/japonês onde o alinhamento foi confirmado.
- Regras de layout específicas para diálogos, escolhas, dicas, missões, itens e descrições do mapa.
- Proteção de controles, número de segmentos e comandos de pausa nas legendas.
- Exportação CSV, geração de P3A e duas formas de compartilhamento: ZIP manual e EXE com restauração.

## Tecnologias e arquitetura

| Camada | Implementação |
| --- | --- |
| Núcleo e integração | Python |
| Interface | HTML, CSS e JavaScript, exibidos com pywebview/WebView2 |
| Persistência | SQLite, transações, WAL, histórico e backups consistentes |
| Tradução automática | DeepL via HTTP |
| Reconstrução | Ingert, KuroTools e PH3 P3A Tool |
| Distribuição | PyInstaller para o Studio; C#/.NET Framework para o instalador |
| Qualidade | `unittest`, fixtures pequenas e testes do motor de instalação C# |

Fluxo principal: **extração → catálogo SQLite → tradução/revisão → validação → reconstrução → pacote → conferência no jogo**.

O catálogo conhecido tem **45.184 registros**, incluindo **129 eventos de cinemáticas com 150 segmentos** e **105 campos internos de perfis/impressões da pesquisa marinha**. Essa contagem descreve o projeto local auditado; não demonstra cobertura absoluta de todos os recursos do jogo. O banco e os textos extraídos não estão neste repositório.

## Decisões e problemas resolvidos

| Problema observado | Tratamento implementado |
| --- | --- |
| Salvar a cada letra atrapalhava a edição. | Texto fica pendente durante a digitação e é salvo ao concluir o trecho ou executar as ações previstas no editor. |
| Frases divididas antes da tradução perdiam continuidade. | Normalização das quebras visuais antes de enviar ao provedor; ajuste do layout depois da resposta. |
| Uma única regra de largura causava cortes em janelas diferentes. | Validação por categoria/campo, sem confundir bytes com largura visual. |
| Algumas cenas continuavam em inglês. | Inclusão de `maya_scene_eng`, preservando estrutura, segmentos e temporização. |
| Instalar manualmente dificultava voltar ao estado anterior. | Instalador com hashes, backup, registro de estado e restauração protegida. |

## Executar o Studio a partir do código

### Requisitos

- Windows com Microsoft Edge WebView2 Runtime.
- Python compatível com `requirements.txt`; a validação local registrada usou Python 3.14.
- Cópia legítima do jogo. Uma extração real também exige as ferramentas externas abaixo.
- Chave do DeepL somente se desejar tradução automática. Revisão manual e testes não exigem chave.

Na raiz deste repositório, pelo PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Para reconstruir recursos reais, forneça localmente:

1. `tools/ingert.exe`: Ingert v1.1.4, obtido do projeto indicado em `THIRD_PARTY_LICENSES.md`.
2. `tools/p3a_tool.exe`: ferramenta da sua instalação compatível do jogo.
3. `.vendor/KuroTools/`: código e schemas do KuroTools, contendo `tbl2json.py`, `json2tbl.py`, `lib/` e `schemas/`.

Nenhuma dessas ferramentas binárias nem recurso do jogo é incluído neste repositório. Coloque o código do KuroTools localmente; não envie a pasta `.vendor` ao GitHub.

Abra o Studio e use **Novo projeto** para extrair sua instalação. O projeto `.ysxproj` fica apenas no seu computador. Configure o provedor no painel de tradução e nunca publique sua chave, banco ou exportações com textos do jogo.

### Gerar o EXE do Studio

Depois de fornecer as dependências externas:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm YsX_PTBR_Studio.spec
```

O resultado fica em `dist/YsX_PTBR_Studio_v2.3.4/`. **Não separe o EXE da pasta `_internal`**. Para criar o instalador da tradução pelo Studio, é necessário o compilador do .NET Framework 4.x no Windows.

## Testes e limitações conhecidas

```powershell
py -m unittest discover -s tests -v
py tools/audit_public_repo.py .
```

Os testes Python usam exemplos pequenos e não exigem jogo, credencial nem chamadas pagas. O teste C# está em `tests/SharingEngineTests.cs`; as instruções estão em [docs/TESTES.md](docs/TESTES.md).

Na conferência de 10/10/2026: **44 testes Python**, **11 verificações do motor C#** e **2 verificações do pacote EXE incorporado** passaram. A pasta pública passou em **46 testes Python** em 20/10/2026, após simplificação para DeepL exclusivo. Consulte [docs/VALIDACAO.md](docs/VALIDACAO.md) para o resultado desta preparação.

Testes de estrutura, integridade, glifos e restauração **não substituem teste visual no jogo**. A revisão integral de cenas, possíveis cortes e progressão permanece necessária. Não se promete funcionamento com outras versões nem tradução de conteúdo ainda não identificado.

## Organização

```text
ysx_studio/        Núcleo, banco, provedores e API local da interface
frontend/          Interface do Studio
applicator_src/    Código C# dos aplicadores
tests/             Testes e fixtures pequenas
tools/             Auditoria e geração
docs/              Arquitetura, estudo técnico e validação
.github/workflows/ Testes automatizados do repositório
```

## Portfólio e contribuição

O projeto demonstra integração de sistemas, investigação de formatos, persistência e rastreabilidade, validação de dados, testes automatizados e distribuição Windows. A documentação de estudo inclui [arquitetura](docs/ARQUITETURA.md), [estudo técnico](docs/ESTUDO_TECNICO.md) e [validação](docs/VALIDACAO.md).

Para relatar um problema, informe a versão, o local/cena, o ID do texto quando disponível e o comportamento esperado. Não inclua chaves, saves pessoais, banco completo ou arquivos originais do jogo.

## Créditos e licença

Créditos de terceiros em [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md). Mantida a licença MIT já existente para o código autoral, conforme [LICENSE](LICENSE). Essa licença **não concede direitos sobre o jogo, a tradução de conteúdo protegido ou ferramentas de terceiros**.

Os arquivos de tradução destinados a jogadores ficam separados do código e sua disponibilização pública depende das permissões aplicáveis. Nenhum upload ou publicação foi feito por esta preparação.
