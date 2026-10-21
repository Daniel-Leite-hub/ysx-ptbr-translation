# Validação da preparação pública — 20/10/2026

Executado diretamente na pasta `Repositorio`, sem usar o banco editorial ou as ferramentas binárias do jogo:

- 48 testes Python: aprovados; inclui DeepL exclusivo e os novos campos internos da pesquisa marinha.
- Auditoria pública por `tools/audit_public_repo.py`: aprovada; sem arquivos binários de jogo/banco nem padrões de credenciais reconhecidos pelo scanner.
- Fonte, testes, fixtures pequenas, documentação e exemplo de glossário selecionados explicitamente; não foi feita uma cópia integral da pasta privada.
- Spec de PyInstaller adaptado para dependências fornecidas localmente na raiz deste repositório.
- Catálogo conhecido atualizado: 45.184 registros; inclui 129 eventos de cinemáticas/150 segmentos e 105 campos internos de pesquisa marinha. O banco não é distribuído no repositório.
- Nenhuma chamada real aos provedores, tradução nova, alteração editorial, instalação no jogo, upload ou push nesta preparação.

Os 11 testes C# de instalação/restauração e 2 testes do pacote incorporado são evidências registradas na entrega de 10/10/2026, não novas execuções feitas nesta etapa.
O Studio privado foi recompilado com a correção de extração. Esta cópia pública não foi compilada separadamente, pois as dependências externas não são redistribuídas nela. Os comandos documentam o preparo necessário.
O teste visual integral no jogo permanece pendente. Contagem de catálogo, hash e round-trip não comprovam cobertura absoluta ou ausência de cortes.

A auditoria automática é uma verificação limitada por regras; não substitui revisão humana das permissões e arquivos antes de publicar.

A interface e a API pública agora aceitam apenas DeepL (Free/Pro). A interface Tkinter legada foi retirada desta cópia; o entrypoint mantido é `main.py`, com WebView.
O nome pessoal e a formação acadêmica foram retirados da apresentação e do aviso de autoria. O banco e o patch privados não foram alterados.
