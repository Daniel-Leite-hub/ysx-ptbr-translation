# Contribuindo

Obrigado pelo interesse no projeto. Contribuições devem preservar o escopo independente, não oficial e voltado à localização PT-BR.

## Antes de abrir uma contribuição

1. Leia o `README.md`, `LEGAL.md` e `SECURITY.md`.
2. Não inclua arquivos originais do jogo, bancos completos, saves, chaves ou dados pessoais.
3. Para mudanças no código, execute:

```powershell
py -m unittest discover -s tests -v
py tools/audit_public_repo.py .
```

4. Descreva claramente o problema, a solução e os testes executados.

## Tradução e compatibilidade

Relatos de tradução devem informar a versão da Release, a cena ou tela, o texto afetado e o comportamento esperado. Sempre que possível, envie uma reprodução mínima sem anexar conteúdo protegido do jogo.

Pull Requests devem ser pequenos e focados. Alterações que afetem instalação, restauração, hashes ou compatibilidade precisam atualizar a documentação correspondente.
