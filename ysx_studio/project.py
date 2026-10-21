from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import core


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS dialogues (
 id INTEGER PRIMARY KEY,
 file_name TEXT NOT NULL,
 kind TEXT NOT NULL,
 source_start INTEGER NOT NULL,
 source_end INTEGER NOT NULL,
 original TEXT NOT NULL,
 translation TEXT NOT NULL DEFAULT '',
 reviewed TEXT NOT NULL DEFAULT '',
 original_bytes INTEGER NOT NULL,
 translated_bytes INTEGER NOT NULL DEFAULT 0,
 original_width INTEGER NOT NULL,
 translated_width INTEGER NOT NULL DEFAULT 0,
 original_lines INTEGER NOT NULL,
 translated_lines INTEGER NOT NULL DEFAULT 0,
 size_ok INTEGER NOT NULL DEFAULT 1,
 tags TEXT NOT NULL,
 context TEXT NOT NULL DEFAULT '',
 provider TEXT NOT NULL DEFAULT '',
 error TEXT NOT NULL DEFAULT '',
 speaker_id TEXT NOT NULL DEFAULT '',
 speaker_name TEXT NOT NULL DEFAULT '',
 speaker_gender TEXT NOT NULL DEFAULT '',
 speaker_confidence TEXT NOT NULL DEFAULT '',
 UNIQUE(file_name, source_start, source_end)
);
CREATE INDEX IF NOT EXISTS idx_dialogue_file ON dialogues(file_name, source_start);
CREATE INDEX IF NOT EXISTS idx_dialogue_status ON dialogues(size_ok, translation, reviewed);
CREATE TABLE IF NOT EXISTS edit_history (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 dialogue_id INTEGER NOT NULL,
 translation TEXT NOT NULL,
 reviewed TEXT NOT NULL,
 saved_at TEXT NOT NULL,
 source TEXT NOT NULL DEFAULT 'manual',
 FOREIGN KEY(dialogue_id) REFERENCES dialogues(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_edit_history_dialogue ON edit_history(dialogue_id, id DESC);
CREATE TABLE IF NOT EXISTS language_context (
 dialogue_id INTEGER NOT NULL REFERENCES dialogues(id) ON DELETE CASCADE,
 language TEXT NOT NULL CHECK(language IN ('es','ja')),
 text TEXT NOT NULL,
 source_file TEXT NOT NULL,
 source_locator TEXT NOT NULL,
 source_sha256 TEXT NOT NULL,
 alignment_method TEXT NOT NULL,
 imported_at TEXT NOT NULL,
 PRIMARY KEY(dialogue_id, language)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=5000")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.executescript(SCHEMA)
    columns = {row[1] for row in db.execute("PRAGMA table_info(dialogues)")}
    if "updated_at" not in columns:
        db.execute("ALTER TABLE dialogues ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''")
    if "revision" not in columns:
        db.execute("ALTER TABLE dialogues ADD COLUMN revision INTEGER NOT NULL DEFAULT 0")
    for column in ("speaker_id", "speaker_name", "speaker_gender", "speaker_confidence"):
        if column not in columns:
            db.execute(f"ALTER TABLE dialogues ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
    db.commit()
    return db


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def checkpoint(db: sqlite3.Connection) -> None:
    db.commit()
    db.execute("PRAGMA wal_checkpoint(FULL)").fetchone()


def backup(db: sqlite3.Connection, project_path: Path, label: str = "checkpoint") -> Path:
    """Cria uma cópia SQLite consistente sem interromper o Studio."""
    destination_dir = project_path.with_suffix("") / "backups"
    destination_dir.mkdir(parents=True, exist_ok=True)
    safe_label = re.sub(r"[^a-zA-Z0-9_-]+", "_", label).strip("_") or "checkpoint"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    destination = destination_dir / f"{project_path.stem}_{safe_label}_{stamp}.ysxproj"
    target = sqlite3.connect(destination)
    try:
        db.backup(target)
    finally:
        target.close()
    # Mantém os 12 backups automáticos mais recentes. Backups pre_v* são preservados.
    automatic = sorted(
        (path for path in destination_dir.glob(f"{project_path.stem}_*.ysxproj")
         if "_pre_v" not in path.name),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for old in automatic[12:]:
        old.unlink()
    return destination


def set_meta(db, key: str, value) -> None:
    db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (key, json.dumps(value, ensure_ascii=False)))


def get_meta(db, key: str, default=None):
    row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else default


def create(game_dir: Path, project_path: Path, progress=None) -> int:
    assets = project_path.with_suffix("")
    decompiled = assets / "decompiled"
    files = core.decompile_scripts(game_dir, decompiled, progress)
    db = connect(project_path)
    db.execute("DELETE FROM dialogues")
    total = len(files)
    for index, path in enumerate(files, 1):
        for row in core.extract_file(path):
            db.execute("""INSERT INTO dialogues(file_name,kind,source_start,source_end,original,
                original_bytes,original_width,original_lines,tags,context)
                VALUES(?,?,?,?,?,?,?,?,?,?)""", (
                row.file_name, row.kind, row.source_start, row.source_end, row.original,
                row.original_bytes, row.original_width, row.original_lines, row.tags, row.context,
            ))
        if progress:
            progress(index, total, f"Catalogando {path.name}")
    table_dir = assets / "tables_original"
    table_files = core.decompile_tables(game_dir, table_dir, progress)
    for path in table_files:
        _upsert_extracted(db, core.extract_table_json(path))
    set_meta(db, "game_dir", str(game_dir.resolve()))
    set_meta(db, "decompiled_dir", str(decompiled.resolve()))
    set_meta(db, "table_json_dir", str(table_dir.resolve()))
    set_meta(db, "format", 1)
    from .cinematics import sync as sync_cinematics
    sync_cinematics(db, project_path, game_dir)
    set_meta(db, "accent_evidence", {"source": "font_mes_eng.fnt + scripts oficiais FR/ES/DE",
                                      "verified": core.PORTUGUESE_GLYPHS})
    db.commit()
    count = db.execute("SELECT COUNT(*) FROM dialogues").fetchone()[0]
    db.close()
    return count


def _upsert_extracted(db: sqlite3.Connection, rows) -> int:
    count = 0
    for row in rows:
        db.execute("""INSERT INTO dialogues(file_name,kind,source_start,source_end,original,
            original_bytes,original_width,original_lines,tags,context)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(file_name,source_start,source_end) DO UPDATE SET
              kind=excluded.kind, original=excluded.original,
              original_bytes=excluded.original_bytes, original_width=excluded.original_width,
              original_lines=excluded.original_lines, tags=excluded.tags, context=excluded.context""", (
            row.file_name, row.kind, row.source_start, row.source_end, row.original,
            row.original_bytes, row.original_width, row.original_lines, row.tags, row.context,
        ))
        count += 1
    return count


def sync_table_catalog(db: sqlite3.Connection, project_path: Path, game_dir: Path,
                       progress=None) -> int:
    """Adiciona/atualiza itens e diário sem apagar traduções já existentes."""
    assets = project_path.with_suffix("")
    table_dir = assets / "tables_original"
    table_files = core.decompile_tables(game_dir, table_dir, progress)
    count = 0
    with db:
        for path in table_files:
            count += _upsert_extracted(db, core.extract_table_json(path))
        set_meta(db, "table_json_dir", str(table_dir.resolve()))
        set_meta(db, "table_catalog_version", 1)
    return count


def sync_script_catalog(db: sqlite3.Connection, project_path: Path,
                        reject_larger: bool = False) -> dict[str, int]:
    """Inclui variantes de comandos de script descobertas após a extração inicial.

    O procedimento nunca remove linhas nem sobrescreve traduções existentes. Para
    novos textos exatamente idênticos a uma tradução já salva, reaproveita somente
    o rascunho automático/manual (não a marca de revisão), deixando a aprovação
    editorial explícita para cada ocorrência.
    """
    decompiled = Path(get_meta(db, "decompiled_dir", project_path.with_suffix("") / "decompiled"))
    if not decompiled.is_dir():
        raise core.StudioError(f"Pasta de scripts extraídos não encontrada: {decompiled}")

    existing = {
        (row["file_name"], row["source_start"], row["source_end"])
        for row in db.execute("SELECT file_name,source_start,source_end FROM dialogues")
    }
    reusable: dict[str, set[str]] = {}
    for row in db.execute("SELECT original,translation FROM dialogues WHERE translation<>''"):
        reusable.setdefault(row["original"], set()).add(row["translation"])

    added = []
    with db:
        for path in sorted(decompiled.glob("*.ing")):
            rows = core.extract_file(path)
            added.extend(
                row for row in rows
                if (row.file_name, row.source_start, row.source_end) not in existing
            )
            _upsert_extracted(db, rows)

        reused = 0
        for row in added:
            candidates = reusable.get(row.original, set())
            if len(candidates) != 1:
                continue
            translation = core.normalize_text_for_kind(
                next(iter(candidates)), row.kind, row.context
            )
            size, width, lines, error, ok = core.validate_text(
                row.original, translation, reject_larger, row.kind, row.context
            )
            saved_at = _timestamp()
            cursor = db.execute("""UPDATE dialogues SET translation=?,provider=?,translated_bytes=?,
                translated_width=?,translated_lines=?,size_ok=?,error=?,updated_at=?,revision=revision+1
                WHERE file_name=? AND source_start=? AND source_end=? AND translation='' AND reviewed=''""", (
                translation, "reused-duplicate", size, width, lines, int(ok), error, saved_at,
                row.file_name, row.source_start, row.source_end,
            ))
            if cursor.rowcount:
                dialogue_id = db.execute("""SELECT id FROM dialogues WHERE file_name=? AND source_start=?
                    AND source_end=?""", (row.file_name, row.source_start, row.source_end)).fetchone()[0]
                db.execute("""INSERT INTO edit_history(dialogue_id,translation,reviewed,saved_at,source)
                    VALUES(?,?,?,?,?)""", (dialogue_id, translation, "", saved_at, "catalog_reuse"))
                reused += 1
        set_meta(db, "script_catalog_version", 3)

    from .cinematics import sync as sync_cinematics
    game_dir = Path(get_meta(db, "game_dir"))
    with db:
        cinematic_added = sync_cinematics(db, project_path, game_dir)
    return {"added": len(added) + cinematic_added, "reused": reused}


def clear_automatic_translations(db: sqlite3.Connection) -> int:
    """Limpa todos os rascunhos automáticos, preservando revisão e histórico."""
    count = db.execute("SELECT COUNT(*) FROM dialogues WHERE translation<>''").fetchone()[0]
    saved_at = _timestamp()
    reviewed = db.execute(
        "SELECT id,original,reviewed,kind,context FROM dialogues WHERE reviewed<>''"
    ).fetchall()
    with db:
        db.execute("""UPDATE dialogues SET translation='',provider='',translated_bytes=0,
            translated_width=0,translated_lines=0,size_ok=1,error='',updated_at=?,revision=revision+1
            WHERE translation<>''""", (saved_at,))
        for row in reviewed:
            size, width, lines, error, ok = core.validate_text(
                row["original"], row["reviewed"], kind=row["kind"], context=row["context"]
            )
            db.execute("""UPDATE dialogues SET translated_bytes=?,translated_width=?,translated_lines=?,
                size_ok=?,error=? WHERE id=?""", (size, width, lines, int(ok), error, row["id"]))
        set_meta(db, "automatic_translation_reset_at", saved_at)
    return int(count)


def stats(db) -> dict[str, int]:
    row = db.execute("""SELECT COUNT(*) total,
      SUM(CASE WHEN translation<>'' THEN 1 ELSE 0 END) translated,
      SUM(CASE WHEN reviewed<>'' THEN 1 ELSE 0 END) reviewed,
      SUM(CASE WHEN error<>'' THEN 1 ELSE 0 END) errors,
      SUM(CASE WHEN (translation<>'' OR reviewed<>'') AND size_ok=0 AND error='' THEN 1 ELSE 0 END) oversized,
      SUM(CASE WHEN translation='' AND reviewed='' THEN 1 ELSE 0 END) pending
      FROM dialogues""").fetchone()
    return {key: int(row[key] or 0) for key in row.keys()}


def sync_speakers(db: sqlite3.Connection, project_path: Path) -> dict[str, int]:
    """Atualiza metadados editoriais de falante sem tocar no texto do jogador."""
    from . import speaker
    result = speaker.sync(db, project_path)
    set_meta(db, "speaker_metadata_version", 1)
    db.commit()
    return result


def effective_text(row) -> str:
    """Texto efetivamente usado: revisão pronta, senão tradução automática."""
    return row["reviewed"] or row["translation"]


def language_context(db: sqlite3.Connection, row_id: int) -> dict[str, dict]:
    """Contexto oficial alinhado; nunca participa da seleção do texto PT-BR."""
    return {row['language']:dict(row) for row in db.execute(
        'SELECT * FROM language_context WHERE dialogue_id=? ORDER BY language', (row_id,))}


def save_text(db, row_id: int, translation: str, reviewed: str, reject_larger: bool,
              source: str = "manual") -> bool:
    row = db.execute("SELECT original,translation,reviewed,file_name,kind,context FROM dialogues WHERE id=?", (row_id,)).fetchone()
    if row is None:
        raise core.StudioError(f"Texto {row_id} não existe no projeto.")
    translation = core.normalize_text_for_kind(translation, row["kind"], row["context"])
    reviewed = core.normalize_text_for_kind(reviewed, row["kind"], row["context"])
    changed = row["translation"] != translation or row["reviewed"] != reviewed
    candidate = effective_text({"translation": translation, "reviewed": reviewed})
    if candidate:
        size, width, lines, error, ok = core.validate_text(
            row[0], candidate, reject_larger, row["kind"], row["context"]
        )
    else:
        size, width, lines, error, ok = 0, 0, 0, "", True
    saved_at = _timestamp()
    with db:
        if changed:
            db.execute("""UPDATE dialogues SET translation=?,reviewed=?,translated_bytes=?,translated_width=?,
                translated_lines=?,size_ok=?,error=?,updated_at=?,revision=revision+1 WHERE id=?""",
                (translation, reviewed, size, width, lines, int(ok), error, saved_at, row_id))
            db.execute("""INSERT INTO edit_history(dialogue_id,translation,reviewed,saved_at,source)
                VALUES(?,?,?,?,?)""", (row_id, translation, reviewed, saved_at, source))
            db.execute("""DELETE FROM edit_history WHERE dialogue_id=? AND id NOT IN
                (SELECT id FROM edit_history WHERE dialogue_id=? ORDER BY id DESC LIMIT 50)""",
                (row_id, row_id))
        else:
            # Mesmo sem alteração textual, a política pode ter mudado ou o
            # registro pode carregar um erro antigo. Recalcule sem criar versão.
            db.execute("""UPDATE dialogues SET translated_bytes=?,translated_width=?,translated_lines=?,
                size_ok=?,error=? WHERE id=?""", (size, width, lines, int(ok), error, row_id))
    return changed


def validate_row(db, row_id: int, reject_larger: bool) -> sqlite3.Row:
    """Revalida somente uma entrada usando revisão, ou tradução como fallback."""
    row = db.execute(
        "SELECT original,translation,reviewed,kind,context FROM dialogues WHERE id=?", (row_id,)
    ).fetchone()
    if row is None:
        raise core.StudioError(f"Texto {row_id} não existe no projeto.")
    candidate = effective_text(row)
    if candidate:
        size, width, lines, error, ok = core.validate_text(
            row["original"], candidate, reject_larger, row["kind"], row["context"]
        )
    else:
        size, width, lines, error, ok = 0, 0, 0, "", True
    with db:
        db.execute("""UPDATE dialogues SET translated_bytes=?,translated_width=?,translated_lines=?,
            size_ok=?,error=? WHERE id=?""", (size, width, lines, int(ok), error, row_id))
    return db.execute("SELECT * FROM dialogues WHERE id=?", (row_id,)).fetchone()


def reflow_script_catalog(db: sqlite3.Connection, reject_larger: bool = False) -> int:
    """Reorganiza em lote quebras prematuras já salvas, com uma versão por linha."""
    rows = db.execute("""SELECT id,original,translation,reviewed,kind,context FROM dialogues
        WHERE file_name NOT LIKE '%.tbl' AND (translation<>'' OR reviewed<>'')""").fetchall()
    changed = 0
    saved_at = _timestamp()
    with db:
        for row in rows:
            translation = core.normalize_text_for_kind(
                row["translation"], row["kind"], row["context"]
            )
            reviewed = core.normalize_text_for_kind(
                row["reviewed"], row["kind"], row["context"]
            )
            candidate = reviewed or translation
            size, width, lines, error, ok = core.validate_text(
                row["original"], candidate, reject_larger, row["kind"], row["context"]
            ) if candidate else (0, 0, 0, "", True)
            different = translation != row["translation"] or reviewed != row["reviewed"]
            db.execute("""UPDATE dialogues SET translation=?,reviewed=?,translated_bytes=?,
                translated_width=?,translated_lines=?,size_ok=?,error=?,
                updated_at=CASE WHEN ? THEN ? ELSE updated_at END,
                revision=revision+? WHERE id=?""",
                (translation, reviewed, size, width, lines, int(ok), error,
                 int(different), saved_at, int(different), row["id"]))
            if different:
                db.execute("""INSERT INTO edit_history(dialogue_id,translation,reviewed,saved_at,source)
                    VALUES(?,?,?,?,?)""", (row["id"], translation, reviewed, saved_at, "reflow_72_v2_1"))
                changed += 1
    return changed


def rows_for_build(db, reject_invalid: bool = True) -> dict[str, list[dict]]:
    # A revisão tem prioridade; até ela existir, usa a tradução automática salva.
    query = "SELECT * FROM dialogues WHERE reviewed<>'' OR translation<>''"
    rows = db.execute(query).fetchall()
    invalid = [row for row in rows if row["error"] or not row["size_ok"]]
    if reject_invalid and invalid:
        raise core.StudioError(f"Há {len(invalid)} texto(s) inválido(s) ou fora do limite.")
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["file_name"], []).append(dict(row))
    return grouped
