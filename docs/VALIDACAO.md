# Validação da preparação pública — 20/10/2026

## Atualização do catálogo de animações — 25/10/2026

- Alterados os módulos públicos de catálogo e reconstrução para reconhecer cinco scripts de animação de combate em `script_eng/ani`.
- O pacote local foi reconstruído e verificado estruturalmente; a reextração encontrou os 74 textos catalogados. O P3A local contém 169 scripts e 39 tabelas, com SHA-256 `66cf5455126b0675f3527984ee3af7be6a22968371144bc43fae03642bb89e55`.
- 20 textos de animação constavam como revisados e 54 como rascunhos na cópia privada; o banco e os conteúdos não são distribuídos neste repositório.
- Esta mudança de código foi sincronizada seletivamente com a edição pública somente DeepL. Não foram copiados banco, arquivos extraídos, patch, executáveis ou credenciais.
- Os testes automatizados não foram reexecutados nesta atualização. A conferência acima é estrutural e não substitui teste visual em jogo; a inspeção das falas de animação continua pendente.

Executado diretamente na pasta `Repositorio`, sem usar o banco editorial ou as ferramentas binárias do jogo:

- 48 testes Python: aprovados; inclui DeepL exclusivo e os novos campos internos da pesquisa marinha.
- Auditoria pública por `tools/audit_public_repo.py`: aprovada; sem arquivos binários de jogo/banco nem padrões de credenciais reconhecidos pelo scanner.
- Fonte, testes, fixtures pequenas, documentação e exemplo de glossário selecionados explicitamente; não foi feita uma cópia integral da pasta privada.
- Spec de PyInstaller adaptado para dependências fornecidas localmente na raiz deste repositório.
- Naquele snapshot de 20/10, o catálogo conhecido tinha 45.184 registros, incluindo 129 eventos de cinemáticas/150 segmentos e 105 campos internos de pesquisa marinha. A contagem foi atualizada para 45.258 em 25/10; o banco não é distribuído no repositório.
- Nenhuma chamada real aos provedores, tradução nova, alteração editorial, instalação no jogo, upload ou push nesta preparação.

Os 11 testes C# de instalação/restauração e 2 testes do pacote incorporado são evidências registradas na entrega de 10/10/2026, não novas execuções feitas nesta etapa.
O Studio privado foi recompilado com a correção de extração. Esta cópia pública não foi compilada separadamente, pois as dependências externas não são redistribuídas nela. Os comandos documentam o preparo necessário.
O teste visual integral no jogo permanece pendente. Contagem de catálogo, hash e round-trip não comprovam cobertura absoluta ou ausência de cortes.

A auditoria automática é uma verificação limitada por regras; não substitui revisão humana das permissões e arquivos antes de publicar.

A interface e a API pública agora aceitam apenas DeepL (Free/Pro). A interface Tkinter legada foi retirada desta cópia; o entrypoint mantido é `main.py`, com WebView.
O nome pessoal e a formação acadêmica foram retirados da apresentação e do aviso de autoria. O banco e o patch privados não foram alterados.
