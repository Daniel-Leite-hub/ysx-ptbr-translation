from __future__ import annotations

import csv
import re
import shutil
import threading
from datetime import datetime
from pathlib import Path

from . import core, project, translator


def translation_config_from_ui(config: dict) -> translator.TranslationConfig:
    provider = config.get("provider", "deepl-free")
    if provider not in {"deepl-free", "deepl-pro", "deepl"}:
        raise core.StudioError("Provedor de tradução inválido.")
    return translator.TranslationConfig(
        provider=provider, api_key=config["api_key"].strip(),
        deepl_glossary_id=config.get("deepl_glossary_id", "").strip(),
        deepl_context=config.get("deepl_context", translator.DEEPL_FANTASY_CONTEXT).strip()
        or translator.DEEPL_FANTASY_CONTEXT)


class WebApi:
    """API local usada exclusivamente pela interface WebView2."""

    def __init__(self, home: Path):
        self.home = Path(home).resolve()
        self.project_path = self._discover_project()
        self.window = None
        self.stop = threading.Event()
        self.worker = None
        self.job = {"running": False, "kind": "", "done": 0, "total": 0, "message": "Pronto"}
        self.last_archive = None

    def _discover_project(self) -> Path | None:
        candidates = [self.home / "YsX_PTBR_Projeto.ysxproj",
                      self.home.parent / "YsX_PTBR_Projeto.ysxproj",
                      self.home.parent.parent / "YsX_PTBR_Projeto.ysxproj"]
        candidates.extend(sorted(self.home.glob("*.ysxproj")))
        candidates.extend(sorted(self.home.parent.glob("*.ysxproj")))
        candidates.extend(sorted(self.home.parent.parent.glob("*.ysxproj")))
        return next((path.resolve() for path in candidates if path.is_file()), None)

    def _need_project(self) -> Path:
        if not self.project_path or not self.project_path.is_file():
            raise core.StudioError("Abra ou crie um projeto Ys X primeiro.")
        return self.project_path

    def call(self, method: str, args: dict):
        allowed = {"overview", "rows", "save", "validate", "history", "open_project",
                   "new_project", "export", "translate", "pause", "revalidate_all",
                   "accent_audit", "sync_scripts", "sync_speakers", "build", "install", "share"}
        if method not in allowed:
            raise core.StudioError("Método desconhecido.")
        return getattr(self, method)(**args)

    def overview(self):
        if not self.project_path or not self.project_path.is_file():
            stats = {"total": 0, "translated": 0, "reviewed": 0, "pending": 0,
                     "oversized": 0, "errors": 0}
            return {**stats, "project": "Nenhum projeto aberto", "project_path": "",
                    "game_dir": "", "job": self.job}
        with project.connect(self.project_path) as db:
            stats = project.stats(db)
            game_dir = project.get_meta(db, "game_dir", "")
            archive = project.get_meta(db, "last_archive", "")
        self.last_archive = Path(archive) if archive else self.last_archive
        return {**stats, "project": self.project_path.name,
                "project_path": str(self.project_path), "game_dir": game_dir, "job": self.job}

    def rows(self, search="", status="all", offset=0, limit=80):
        path = self._need_project()
        clauses, params = [], []
        requested_tags = []
        def remove_tag(match):
            requested_tags.append(core.normalize_content_tag(match.group(1)))
            return " "
        text_search = re.sub(r"(?i)(?:^|\s)#?tag:([^\s]+)", remove_tag, search).strip()
        if text_search:
            clauses.append("(original LIKE ? OR translation LIKE ? OR reviewed LIKE ? OR file_name LIKE ?)")
            params.extend([f"%{text_search}%"] * 4)
        status_sql = {
            "pending": "translation='' AND reviewed=''",
            "translated": "translation<>'' AND reviewed=''",
            "reviewed": "reviewed<>''",
            "issues": "(translation<>'' OR reviewed<>'') AND (error<>'' OR size_ok=0)",
        }
        if status in status_sql:
            clauses.append(status_sql[status])
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        offset, limit = max(0, int(offset)), min(100, max(1, int(limit)))
        db = project.connect(path)
        try:
            if requested_tags:
                candidates = [dict(row) for row in db.execute(
                    "SELECT * FROM dialogues" + where + " ORDER BY id", params)]
                for row in candidates:
                    row["content_tags"] = list(core.content_tags(
                        row["file_name"], row["kind"], row["context"]))
                matches = [row for row in candidates if all(
                    tag in row["content_tags"] for tag in requested_tags)]
                total, data = len(matches), matches[offset:offset + limit]
            else:
                total = db.execute("SELECT COUNT(*) FROM dialogues" + where, params).fetchone()[0]
                data = [dict(row) for row in db.execute(
                    "SELECT * FROM dialogues" + where + " ORDER BY id LIMIT ? OFFSET ?",
                    [*params, limit, offset])]
                for row in data:
                    row["content_tags"] = list(core.content_tags(
                        row["file_name"], row["kind"], row["context"]))
        finally:
            db.close()
        return {"total": total, "items": data}

    def save(self, id, translation, reviewed, strict=False, source="web", approve=False):
        translation = core.wrap_visual_lines(translation)
        reviewed = core.wrap_visual_lines(reviewed)
        with project.connect(self._need_project()) as db:
            if approve:
                row = db.execute("SELECT original,kind,context FROM dialogues WHERE id=?", (int(id),)).fetchone()
                if row is None:
                    raise core.StudioError("Texto não encontrado.")
                if not reviewed:
                    raise core.StudioError("Preencha o texto final antes de aprovar.")
                _size, _width, _lines, error, ok = core.validate_text(
                    row["original"], reviewed, bool(strict), row["kind"], row["context"])
                if not ok:
                    raise core.StudioError("Corrija a linha antes de marcar como revisada: " + error)
            project.save_text(db, int(id), translation, reviewed, bool(strict), source)
            return dict(db.execute("SELECT * FROM dialogues WHERE id=?", (int(id),)).fetchone())

    def validate(self, id, strict=False):
        with project.connect(self._need_project()) as db:
            return dict(project.validate_row(db, int(id), bool(strict)))

    def history(self, id):
        with project.connect(self._need_project()) as db:
            return [dict(row) for row in db.execute(
                "SELECT * FROM edit_history WHERE dialogue_id=? ORDER BY id DESC LIMIT 25", (int(id),))]

    def open_project(self):
        if not self.window:
            raise core.StudioError("Janela ainda não está pronta.")
        import webview
        selected = self.window.create_file_dialog(
            webview.OPEN_DIALOG, directory=str(self.home), allow_multiple=False,
            file_types=("Projeto Ys X (*.ysxproj)",))
        if not selected:
            return None
        path = Path(selected[0]).resolve()
        db = project.connect(path)
        try:
            project.backup(db, path, "abertura_web")
        finally:
            db.close()
        self.project_path = path
        return self.overview()

    def new_project(self):
        if self.job["running"]:
            raise core.StudioError("Aguarde a operação atual terminar.")
        if not self.window:
            raise core.StudioError("Janela ainda não está pronta.")
        import webview
        folders = self.window.create_file_dialog(webview.FOLDER_DIALOG, directory=str(self.home.parent))
        if not folders:
            return None
        game = Path(folders[0]).resolve()
        selected = self.window.create_file_dialog(
            webview.SAVE_DIALOG, directory=str(game), save_filename="YsX_PTBR_Projeto.ysxproj",
            file_types=("Projeto Ys X (*.ysxproj)",))
        if not selected:
            return None
        target = Path(selected[0] if isinstance(selected, (tuple, list)) else selected).resolve()
        if target.suffix.lower() != ".ysxproj":
            target = target.with_suffix(".ysxproj")
        self.job = {"running": True, "kind": "extract", "done": 0, "total": 1,
                    "message": "Preparando extração…"}

        def progress(done, total, message):
            self.job = {"running": True, "kind": "extract", "done": done,
                        "total": total, "message": message}

        def work():
            try:
                count = project.create(game, target, progress)
                self.project_path = target
                self.job["message"] = f"Projeto criado com {count:,} textos."
            except Exception as exc:
                self.job["message"] = str(exc)
            finally:
                self.job["running"] = False

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()
        return {"started": True, "path": str(target)}

    def export(self):
        path = self._need_project()
        output = path.with_suffix("") / "textos_traduzidos.csv"
        output.parent.mkdir(parents=True, exist_ok=True)
        with project.connect(path) as db, output.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream, delimiter=";")
            writer.writerow(("id", "arquivo", "tipo", "tags_busca", "original_ingles", "traducao_automatica",
                             "tamanho", "texto_final_revisado", "fonte_usada_no_jogo",
                             "texto_usado_no_jogo"))
            for row in db.execute("SELECT * FROM dialogues ORDER BY id"):
                status = "CERTO" if row["size_ok"] and not row["error"] else "ERRADO: " + row["error"]
                source = "revisão final" if row["reviewed"] else (
                    "tradução automática" if row["translation"] else "vazio")
                content_tags = " ".join(f"tag:{tag}" for tag in core.content_tags(
                    row["file_name"], row["kind"], row["context"]))
                writer.writerow((row["id"], row["file_name"], row["kind"], content_tags, row["original"],
                                 row["translation"], status, row["reviewed"], source,
                                 project.effective_text(row)))
        return str(output)

    def translate(self, config):
        if self.job["running"]:
            raise core.StudioError("Já existe uma operação em andamento.")
        if not config.get("api_key", "").strip():
            raise core.StudioError("Informe a chave da API.")
        path = self._need_project()
        settings = translation_config_from_ui(config)
        self.stop.clear()
        self.job = {"running": True, "kind": "translate", "done": 0, "total": 0,
                    "message": "Preparando tradução…"}

        def progress(done, total):
            self.job = {"running": True, "kind": "translate", "done": done,
                        "total": total, "message": f"{done:,} de {total:,} textos salvos"}

        def work():
            try:
                with project.connect(path) as db:
                    translator.run_queue(db, settings, bool(config.get("strict")), progress,
                                         self.stop.is_set)
                    project.checkpoint(db)
                self.job["message"] = "Tradução concluída; todos os lotes foram salvos."
            except Exception as exc:
                self.job["message"] = str(exc)
            finally:
                config["api_key"] = ""
                self.job["running"] = False

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()
        return True

    def pause(self):
        self.stop.set()
        self.job["message"] = "Parada solicitada; salvando o lote atual…"
        return True

    def revalidate_all(self, strict=False):
        path = self._need_project()
        with project.connect(path) as db:
            rows = db.execute("SELECT id,translation,reviewed FROM dialogues").fetchall()
            for row in rows:
                project.save_text(db, row["id"], row["translation"], row["reviewed"],
                                  bool(strict), "quebra_72")
                project.validate_row(db, row["id"], bool(strict))
        return len(rows)

    def accent_audit(self):
        with project.connect(self._need_project()) as db:
            game = Path(project.get_meta(db, "game_dir"))
        result = core.font_support_report(game)
        missing = [char for char, present in result.items() if not present]
        return {"verified": len(result) - len(missing), "total": len(result),
                "missing": "".join(missing), "test": core.PORTUGUESE_TEST}

    def sync_scripts(self, strict=False):
        """Atualiza o catálogo sem uma nova extração ou perda de edições."""
        path = self._need_project()
        with project.connect(path) as db:
            project.backup(db, path, "antes_de_sincronizar_scripts")
            return project.sync_script_catalog(db, path, bool(strict))

    def sync_speakers(self):
        """Preenche os metadados de falante/gênero sem modificar traduções."""
        path = self._need_project()
        with project.connect(path) as db:
            return project.sync_speakers(db, path)

    def build(self):
        path = self._need_project()
        if self.job["running"]:
            raise core.StudioError("Aguarde ou pause a operação atual.")
        with project.connect(path) as db:
            project.backup(db, path, "antes_do_build_web")
            grouped = project.rows_for_build(db, reject_invalid=True)
            game = Path(project.get_meta(db, "game_dir"))
            decompiled = Path(project.get_meta(db, "decompiled_dir"))
            table_json_dir = Path(project.get_meta(db, "table_json_dir", ""))
        if not grouped:
            raise core.StudioError("Ainda não há traduções para inserir.")
        output = path.with_suffix("") / "build"
        script_rows = {name: rows for name, rows in grouped.items() if not name.lower().endswith(".tbl")}
        table_rows = {name: rows for name, rows in grouped.items() if name.lower().endswith(".tbl")}
        sources = core.build_sources(decompiled, output / "sources", script_rows)
        tables = core.compile_tables(table_json_dir, output / "tables", table_rows) if table_rows else []
        archive = core.compile_mod(game, output / "sources", output, sources, tables)
        with project.connect(path) as db:
            project.set_meta(db, "last_archive", str(archive)); db.commit()
        self.last_archive = archive
        return {"path": str(archive), "files": len(sources) + len(tables)}

    def install(self):
        path = self._need_project()
        with project.connect(path) as db:
            archive = self.last_archive or Path(project.get_meta(db, "last_archive", ""))
            game = Path(project.get_meta(db, "game_dir"))
        if not archive or not Path(archive).is_file():
            raise core.StudioError("Gere o P3A antes de instalar.")
        destination = game / "mods" / "zzz_ysx_ptbr.p3a"
        destination.parent.mkdir(parents=True, exist_ok=True)
        backup = None
        if destination.exists():
            backup_dir = destination.parent / "backup_ptbr" / datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup = backup_dir / destination.name
            shutil.copy2(destination, backup)
        shutil.copy2(archive, destination)
        return {"path": str(destination), "backup": str(backup) if backup else ""}

    def share(self, mode: str):
        from . import sharing
        if mode not in {"zip", "exe"}:
            raise core.StudioError("Formato de compartilhamento inválido.")
        # Rebuild from saved state, never share a stale archive.
        result = self.build()
        path = self._need_project()
        with project.connect(path) as db:
            game = Path(project.get_meta(db, "game_dir"))
        return sharing.generate(Path(result["path"]), game,
                                path.parent / "Compartilhamento", mode)
