# Build local: supply tools/*.exe and .vendor/KuroTools yourself.
from pathlib import Path
root = Path(SPECPATH)
kuro = root / '.vendor' / 'KuroTools'
a = Analysis(['main.py'], pathex=[str(root)],
    binaries=[(str(root/'tools/ingert.exe'), 'tools'), (str(root/'tools/p3a_tool.exe'), 'tools')],
    datas=[(str(root/'frontend'), 'frontend'),
           (str(root/'applicator_src/CompartilharTraducao.cs'), 'applicator_src'),
           (str(kuro/'tbl2json.py'), 'kurotools'), (str(kuro/'json2tbl.py'), 'kurotools'),
           (str(kuro/'lib'), 'kurotools/lib'), (str(kuro/'schemas'), 'kurotools/schemas'),
           (str(root/'docs/examples/glossario_exemplo.csv'), '.'),
           (str(root/'THIRD_PARTY_LICENSES.md'), '.'), (str(root/'README.md'), '.')],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='YsX_PTBR_Studio_v2.3.4',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name='YsX_PTBR_Studio_v2.3.4')
