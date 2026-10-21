# Testes

## Python (sem jogo ou APIs)

Na raiz do repositório:

```powershell
py -m unittest discover -s tests -v
py tools/audit_public_repo.py .
```

## Motor C# do instalador

No PowerShell do Windows, com .NET Framework 4.x:

```powershell
New-Item -ItemType Directory -Force build | Out-Null
$repo = (Get-Location).Path
$compiler = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
& $compiler /nologo /target:exe /main:SharingEngineTests "/out:$repo\build\SharingEngineTests.exe" /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Web.Extensions.dll "$repo\applicator_src\CompartilharTraducao.cs" "$repo\tests\SharingEngineTests.cs"
& "$repo\build\SharingEngineTests.exe" "$repo\build\simulacao_instalacao"
```

Use uma pasta de simulação nova a cada rodada. Nunca indique a pasta real do jogo como destino do teste.
São conferidos versão/patch incompatível, instalação e remoção, reinstalação, recuperação de estado interrompido,
proteção de modificações externas, caminho de backup e corrupção do backup.

Se possuir um pacote de distribuição real, o mesmo teste aceita `--verify-package CAMINHO_ABSOLUTO_DO_EXE` para verificar
o manifesto e hash do patch com o parser .NET Framework. Isso não inicia o jogo nem comprova apresentação visual.
