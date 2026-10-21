"""Metadados de falante e gênero extraídos de chamadas de diálogo Ys X."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

SPEAKER_CALL_RE = re.compile(r"system\[5,11\]\(\s*(\d+)")

# IDs de janela de diálogo confirmados por autoapresentação literal no roteiro
# (por exemplo, "My name is Einar"), além dos perfis oficiais do jogo.
# Diferentemente dos IDs de voz, estes permanecem estáveis entre roteiros.
CURATED_SPEAKERS = {
    "101": ("Dr. Flair", "masculino", "confirmado pelo roteiro"),
    "151": ("Lila", "feminino", "confirmado pelo roteiro"),
    "201": ("Grenn", "masculino", "confirmado pelo roteiro"),
    "202": ("Rosalind", "feminino", "confirmado pelo roteiro"),
    "251": ("Phylleia", "feminino", "confirmado pelo roteiro"),
    "252": ("Gunnar", "masculino", "confirmado pelo roteiro"),
    "253": ("Einar", "masculino", "confirmado pelo roteiro"),
    "1005": ("Romes", "masculino", "confirmado pelo roteiro"),
    "1006": ("Lux", "masculino", "confirmado pelo roteiro"),
    "1008": ("Cohen", "masculino", "confirmado pelo roteiro"),
    "1011": ("Guila", "feminino", "confirmado pelo roteiro"),
    "1012": ("Dawson", "masculino", "confirmado pelo roteiro"),
    "1013": ("Ashley", "masculino", "confirmado pelo roteiro"),
    "1015": ("Mandy", "masculino", "confirmado pelo roteiro"),
    "1016": ("Cuthbert", "masculino", "confirmado pelo roteiro"),
    "1104": ("Ezer", "masculino", "confirmado pelo roteiro"),
    "1117": ("Ornella", "feminino", "confirmado pelo roteiro"),
}
# Alguns IDs de voz são genéricos e reutilizados pelo jogo. Nestes casos,
# a identidade só é confiável no roteiro/cena indicado, nunca globalmente.
CONTEXTUAL_SPEAKERS = {
    ("mp_m1220.ing", "1010"): ("Millette", "feminino", "confirmado pelo roteiro"),
}
PROFILE_GENDERS = {
    "Adol": "masculino", "Karja": "feminino", "Dogi": "masculino",
    "Dr. Flair": "masculino", "Grenn": "masculino", "Rosalind": "feminino",
    "Cruz": "masculino", "Mirabel": "feminino", "Rafe": "masculino",
    "Lila": "feminino", "Phylleia": "feminino", "Ezer": "masculino",
    "Clement": "masculino", "Gulliver": "masculino", "René": "masculino",
    "Corinne": "feminino", "Momina": "feminino", "Joel": "masculino",
    "Romes": "masculino", "Millette": "feminino", "Guila": "feminino",
    "Dawson": "masculino", "Ashley": "masculino", "Mandy": "masculino",
    "Cuthbert": "masculino", "Einar": "masculino", "Hugill": "masculino",
    "Lux": "masculino", "Sache": "feminino", "Cohen": "masculino",
    "Grimson": "masculino", "Gunnar": "masculino", "Canute": "masculino",
    "Astrid": "feminino", "Mysterious Old Man": "masculino",
    "Nameless Old Man": "masculino", "The Snowfrost Witch": "feminino",
}


def _profile_voice_map(project_path: Path) -> dict[str, tuple[str, str, str]]:
    """Lê os IDs de voz ligados aos perfis oficiais de personagem."""
    source = project_path.with_suffix("") / "tables_original" / "t_character_lib.json"
    if not source.is_file():
        return {}
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
        records = next(item["data"] for item in document["data"] if item["name"] == "CharaLibData")
    except (OSError, ValueError, KeyError, StopIteration):
        return {}
    candidates: dict[str, set[str]] = {}
    for record in records:
        name = record.get("text1", "")
        if not name or name not in PROFILE_GENDERS:
            continue
        for voice_id in record.get("arr4", []):
            if isinstance(voice_id, int):
                candidates.setdefault(str(voice_id), set()).add(name)
    result = {}
    for voice_id, names in candidates.items():
        if len(names) == 1:
            name = next(iter(names))
            result[voice_id] = (name, PROFILE_GENDERS[name], "confirmado pelo perfil")
    return result


def classify(row: sqlite3.Row, project_path: Path,
             voice_map: dict[str, tuple[str, str, str]]) -> tuple[str, str, str, str]:
    if row["context"].startswith("ResearchData"):
        locator = json.loads(row["context"].rsplit("\n", 1)[-1])
        identity = str(locator.get("speaker_id", ""))
        name, gender, confidence = CURATED_SPEAKERS.get(identity,
            voice_map.get(identity, ("", "", "não identificado")))
        return identity, name, gender, confidence
    if row["kind"] == "legenda/cinemática":
        locator = json.loads(row["context"].rsplit("\n", 1)[-1])
        identity = locator.get("speaker", "")
        name = {"KARGIA": "Karja", "RILA": "Lila", "RILA_2": "Lila", "ELDER": "Rollo",
                "ROLLO_2": "Rollo", "ADOL": "Adol", "GRENN": "Grenn", "CRUZ": "Cruz",
                "PHYLLEIA": "Phylleia", "ROSALIND": "Rosalind", "MIRABEL": "Mirabel",
                "GRIMSON": "Grimson", "GUNNAR": "Gunnar"}.get(identity, identity)
        gender = PROFILE_GENDERS.get(name, "")
        if identity in {"ELDER", "ROLLO_2"}:
            gender = "masculino"
        return identity, name, gender, ("CHR_NAME da cinemática + perfil/roteiro" if gender else "não identificado")
    if row["kind"] == "escolha":
        return "jogador", "Adol", "masculino", "confirmado pela escolha do jogador"
    match = SPEAKER_CALL_RE.search(row["context"] or "")
    if not match:
        return "", "", "", "não identificado"
    speaker_id = match.group(1)
    if speaker_id == "65535":
        return speaker_id, "Narrador", "", "confirmado por chamada narrativa"
    file_name = row["file_name"] if "file_name" in row.keys() else ""
    name, gender, confidence = CONTEXTUAL_SPEAKERS.get(
        (file_name, speaker_id), CURATED_SPEAKERS.get(
        speaker_id, voice_map.get(speaker_id, ("", "", "não identificado"))
    ))
    return speaker_id, name, gender, confidence


def sync(db: sqlite3.Connection, project_path: Path) -> dict[str, int]:
    """Preenche apenas metadados; não altera original, tradução ou revisão."""
    voice_map = _profile_voice_map(project_path)
    rows = db.execute("SELECT id,file_name,kind,context FROM dialogues").fetchall()
    updated = known = 0
    with db:
        for row in rows:
            speaker_id, name, gender, confidence = classify(row, project_path, voice_map)
            if name and gender:
                known += 1
            result = db.execute("""UPDATE dialogues SET speaker_id=?,speaker_name=?,speaker_gender=?,
                speaker_confidence=? WHERE id=? AND (speaker_id<>? OR speaker_name<>? OR
                speaker_gender<>? OR speaker_confidence<>?)""", (
                speaker_id, name, gender, confidence, row["id"],
                speaker_id, name, gender, confidence,
            ))
            updated += result.rowcount
    return {"total": len(rows), "known_gender": known, "updated": updated}
