"""Gera um P3A reproduzível a partir do estado salvo no projeto SQLite."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ysx_studio import core, project


def main() -> None:
    project_path = ROOT / "YsX_PTBR_Projeto.ysxproj"
    output = project_path.with_suffix("") / "release_build"
    db = project.connect(project_path)
    try:
        backup = project.backup(db, project_path, "antes_release")
        grouped = project.rows_for_build(db, reject_invalid=True)
        game = Path(project.get_meta(db, "game_dir"))
        decompiled = Path(project.get_meta(db, "decompiled_dir"))
        table_json = Path(project.get_meta(db, "table_json_dir", ""))
    finally:
        db.close()

    script_rows = {name: rows for name, rows in grouped.items() if not name.lower().endswith(".tbl")}
    table_rows = {name: rows for name, rows in grouped.items() if name.lower().endswith(".tbl")}
    sources = core.build_sources(decompiled, output / "sources", script_rows)
    tables = core.compile_tables(table_json, output / "tables", table_rows) if table_rows else []

    def progress(done, total, name):
        if done == total or done == 1 or done % 10 == 0:
            print(f"[{done}/{total}] {name}", flush=True)

    archive = core.compile_mod(game, output / "sources", output, sources, tables, progress)
    core.run_tool([str(core.find_tool("p3a_tool.exe", game)), "verify", str(archive)])
    with project.connect(project_path) as db:
        project.set_meta(db, "last_archive", str(archive))
        project.set_meta(db, "release_archive_sha256", core.file_sha256(archive))
        db.commit()
    print({"archive": str(archive), "sha256": core.file_sha256(archive),
           "scripts": len(sources), "tables": len(tables), "backup": str(backup)})


if __name__ == "__main__":
    main()
