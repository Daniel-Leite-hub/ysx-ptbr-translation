"""Private sharing artifacts. No credentials, database or original game assets."""
import json
import zipfile
from pathlib import Path
from . import core


def generate(archive: Path, game: Path, output: Path, mode: str):
    if mode not in {"zip", "exe"}:
        raise core.StudioError("Formato de compartilhamento inválido.")
    archive, game, output = Path(archive), Path(game), Path(output)
    if not archive.is_file():
        raise core.StudioError("Gere o patch antes de compartilhar.")
    core.run_tool([str(core.find_tool("p3a_tool.exe", game)), "verify", str(archive)])
    glyphs = core.font_support_report(game)
    if not all(glyphs.values()):
        raise core.StudioError("Fontes nativas não cobrem PT-BR; prepare um patch de fonte antes de compartilhar.")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"version": "Ys X Proud Nordics 1.0.3_r10",
                "exe_sha256": core.file_sha256(game / "ysx_pn.exe"),
                "script_sha256": core.file_sha256(game / "script.p3a"),
                "patch_sha256": core.file_sha256(archive),
                "verified_glyphs": glyphs,
                "fonts": "Fontes nativas compatíveis com PT-BR; nenhuma fonte original redistribuída."}
    guide = """YS X PROUD NORDICS — TRADUÇÃO PT-BR
Compatibilidade: versão 1.0.3_r10 da instalação usada para gerar este pacote.
Use o idioma inglês. Feche o jogo antes de instalar ou desfazer.

ZIP MANUAL
1. Se existir mods/zzz_ysx_ptbr.p3a, copie-o para uma pasta de backup fora do ZIP.
2. Extraia este ZIP na pasta que contém ysx_pn.exe, mantendo a pasta mods.
3. Reabra o jogo. As fontes nativas já suportam os acentos do português.
4. Para desfazer: retire APENAS mods/zzz_ysx_ptbr.p3a e recoloque o mod salvo
   no passo 1, se havia um. Não exclua a pasta mods nem outros mods.

EXE COM RESTAURAÇÃO
O EXE é autossuficiente: não requer Python, Studio ou acesso à internet.
Selecione a pasta do jogo. Ele confere os hashes de versão e do patch,
preserva o mod anterior, registra o estado e aplica somente o mod PT-BR.
Para desfazer, abra o mesmo EXE e clique Restaurar / desfazer.
Backups e log ficam em mods/backup_ptbr e mods/ysx_ptbr.log.
Alterações externas no mod bloqueiam a restauração para não perder seu trabalho.
O modo de restauração automática só atende instalações registradas pelo EXE.

Não inclui ROM, executável original, banco, chaves de API ou fontes comerciais.
Validação estrutural não substitui conferência visual dentro do jogo.
"""
    data = json.dumps(manifest, ensure_ascii=False, indent=2)
    if mode == "zip":
        target = output / "YsX_PTBR_Copiar_na_Pasta_do_Jogo.zip"
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as package:
            package.write(archive, "mods/zzz_ysx_ptbr.p3a")
            package.writestr("LEIA_ME_PTBR.txt", guide)
            package.writestr("manifesto_ptbr.json", data)
        with zipfile.ZipFile(target) as package:
            if package.testzip():
                raise core.StudioError("Falha na integridade do ZIP.")
    else:
        source = core.resource_path("applicator_src", "CompartilharTraducao.cs")
        compiler = Path("C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe")
        if not compiler.exists():
            raise core.StudioError("Compilador .NET Framework não disponível para gerar o instalador.")
        metadata = output / "manifesto_instalador.json"
        metadata.write_text(data, encoding="utf-8")
        target = output / "Instalar_YsX_PTBR.exe"
        core.run_tool([str(compiler), "/nologo", "/target:winexe", "/out:" + str(target),
                       "/reference:System.Windows.Forms.dll", "/reference:System.Drawing.dll",
                       "/reference:System.Web.Extensions.dll", "/resource:" + str(archive) + ",patch.p3a",
                       "/resource:" + str(metadata) + ",manifest.json", str(source)])
    (output / "LEIA_ME_PTBR.txt").write_text(guide, encoding="utf-8")
    return {"path": str(target), "sha256": core.file_sha256(target), "mode": mode}
