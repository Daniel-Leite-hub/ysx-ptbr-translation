"""Maya Scene JSON: one editorial record per timed subtitle event.

JSON paths, not voice IDs (DLG_DUMMY repeats), identify each occurrence.
Only subtitle values may change; animation, audio and timing remain intact.
"""
import json
import shutil
from pathlib import Path


KIND = "legenda/cinemática"


def events(node, pointer=()):
    if isinstance(node, dict):
        subtitles = node.get("SUBTITLE")
        if isinstance(subtitles, list) and subtitles:
            if not all(isinstance(part, dict) and len(part) == 1
                       and isinstance(next(iter(part.values())), str) for part in subtitles):
                raise ValueError(f"Unsupported SUBTITLE structure: {pointer}")
            if any(next(iter(part.values())).strip() for part in subtitles):
                yield pointer, node
        for key, child in node.items():
            yield from events(child, pointer + (key,))
    elif isinstance(node, list):
        for index, child in enumerate(node):
            yield from events(child, pointer + (index,))


def event_text(event):
    return "\n".join(next(iter(part.values())) for part in event["SUBTITLE"])


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def extract(path):
    from . import core
    result = []
    for serial, (pointer, event) in enumerate(events(load(path)), 1):
        original = event_text(event)
        size, width, lines = core.text_metrics(original)
        locator = {"maya_pointer": pointer, "voice": event.get("DIALOGUE_ID", ""),
                   "speaker": event.get("CHR_NAME", ""), "time": event.get("EVENT_TIME")}
        result.append(core.ExtractedText(
            "maya_scene_eng/" + Path(path).name, KIND, serial, serial + 1, original,
            size, width, lines, core.tags_signature(original),
            "Cinemática · " + locator["speaker"] + " · " + locator["voice"] + "\n"
            + json.dumps(locator, ensure_ascii=False, separators=(",", ":"))))
    return result


def patch(document, rows):
    from . import core
    for row in rows:
        final = row["reviewed"] or row["translation"]
        if not final:
            continue
        event = document
        for key in json.loads(row["context"].rsplit("\n", 1)[-1])["maya_pointer"]:
            event = event[key]
        if event_text(event) != row["original"]:
            raise core.StudioError("Fonte da cinemática mudou; reextração exige revisão.")
        _, _, _, error, ok = core.validate_text(row["original"], final, kind=KIND)
        if not ok:
            raise core.StudioError(error)
        for part, line in zip(event["SUBTITLE"], final.split("\n"), strict=True):
            part[next(iter(part))] = line
    return document


def sync(db, project_path, game_dir):
    from . import core, project
    destination = project_path.with_suffix("") / "decompiled" / "maya_scene_eng"
    destination.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in sorted((game_dir / "maya_scene_eng").glob("*.maya_scene")):
        snapshot = destination / path.name
        if snapshot.exists() and snapshot.read_bytes() != path.read_bytes():
            raise core.StudioError(f"Original Maya alterado: {path.name}; snapshot preservado.")
        if not snapshot.exists():
            shutil.copy2(path, snapshot)
        extracted = extract(snapshot)
        for row in extracted:
            old = db.execute("SELECT original FROM dialogues WHERE file_name=? AND source_start=? AND source_end=?",
                             (row.file_name, row.source_start, row.source_end)).fetchone()
            if old and old[0] != row.original:
                raise core.StudioError("Catálogo Maya mudou; traduções preservadas.")
            count += int(old is None)
        project._upsert_extracted(db, extracted)
    project.set_meta(db, "cinematic_catalog_version", 1)
    return count
