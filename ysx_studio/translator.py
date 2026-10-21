from __future__ import annotations

import html
import json
import random
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from . import core, project


DEEPL_FANTASY_CONTEXT = (
    "Ys X is a fantasy action RPG. Translate from English into natural Brazilian Portuguese. "
    "Treat each text as one continuous sentence or paragraph even when it contains visual line breaks. "
    "Preserve all tags, commands, variables and formatting markers. Use polished, immersive fantasy "
    "dialogue and adapt the register to the situation: formal or heroic for royalty, rituals and legends; "
    "warm and emotional for personal scenes; natural conversational language for companions; and light "
    "humor when appropriate. Keep names, terminology and world-building consistent."
)


@dataclass(frozen=True)
class TranslationConfig:
    provider: str
    api_key: str
    batch_characters: int = 8_000
    batch_items: int = 50
    deepl_glossary_id: str = ""
    deepl_context: str = DEEPL_FANTASY_CONTEXT


PROTECTED_RE = re.compile(f"({core.CONTROL_RE.pattern})")


def normalize_deepl_source(text: str) -> str:
    """Remove quebras visuais antes de enviar o sentido completo ao DeepL.

    Scripts do jogo usam quebras para posicionar texto na tela, não para separar
    parágrafos semânticos. Uma palavra cortada por hífen é reunida; as demais
    quebras viram um único espaço. Tags e comandos continuam intactos e são
    protegidos na etapa seguinte.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"(?i)(?:&#x0*20;|&#0*32;|&nbsp;)", " ", normalized)
    normalized = re.sub(r"(?<=\w)-[ \t]*\n[ \t]*(?=\w)", "", normalized)
    normalized = re.sub(r"[ \t]*\n+[ \t]*", " ", normalized)
    return re.sub(r"[ \t]{2,}", " ", normalized).strip()


def _protect(text: str):
    tokens, output = {}, []
    for part in PROTECTED_RE.split(text):
        if not part:
            continue
        if PROTECTED_RE.fullmatch(part):
            key = f"__YSX{len(tokens):04d}__"
            tokens[key] = part
            output.append(f"<x>{key}</x>")
        else:
            output.append("<br/>".join(html.escape(piece) for piece in part.split("\n")))
    return "<r>" + "".join(output) + "</r>", tokens


def _restore(text: str, tokens: dict[str, str]) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</?(?:r|x)(?:\s[^>]*)?>", "", text, flags=re.I)
    text = html.unescape(text)
    for key, value in tokens.items():
        text = text.replace(key, value).replace(key.lower(), value)
    if any(value not in text for value in tokens.values()):
        raise core.StudioError("A API removeu ou alterou uma tag protegida.")
    return text


def _request(url, body, headers, timeout=45, retries=7):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    for attempt in range(retries):
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt + 1 == retries:
                detail = exc.read().decode("utf-8", "replace")
                raise core.StudioError(f"HTTP {exc.code}: {detail[:600]}") from exc
            retry = exc.headers.get("Retry-After", "")
            time.sleep(float(retry) if retry.isdigit() else min(60, 2 ** attempt + random.random()))
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt + 1 == retries:
                raise core.StudioError(str(exc)) from exc
            time.sleep(min(60, 2 ** attempt + random.random()))


def deepl_endpoint(config: TranslationConfig) -> str:
    """Retorna o host oficial conforme o plano DeepL selecionado."""
    if config.provider == "deepl-free":
        return "https://api-free.deepl.com"
    if config.provider == "deepl-pro":
        return "https://api.deepl.com"
    if config.provider == "deepl":
        return "https://api-free.deepl.com" if config.api_key.endswith(":fx") else "https://api.deepl.com"
    raise core.StudioError("Provedor não suportado. Selecione DeepL Free ou Pro.")


def translate_batch(config: TranslationConfig, texts: list[str]) -> list[str]:
    prepared = [_protect(normalize_deepl_source(text)) for text in texts]
    endpoint = deepl_endpoint(config)
    body = {"text": [text for text, _ in prepared], "source_lang": "EN", "target_lang": "PT-BR",
            "context": config.deepl_context.strip() or DEEPL_FANTASY_CONTEXT,
            "preserve_formatting": False, "split_sentences": "1",
            "tag_handling": "xml", "tag_handling_version": "v2",
            "ignore_tags": ["x"], "non_splitting_tags": ["x"]}
    if config.deepl_glossary_id:
        body["glossary_id"] = config.deepl_glossary_id
    result = _request(endpoint + "/v2/translate", body,
                      {"Content-Type": "application/json", "Authorization": f"DeepL-Auth-Key {config.api_key}"})
    translated = [item["text"] for item in result["translations"]]
    return [_restore(text, tokens) for text, (_, tokens) in zip(translated, prepared, strict=True)]


def run_queue(db, config: TranslationConfig, reject_larger=False, progress=None, should_stop=None):
    rows = db.execute("SELECT id,original,file_name,kind,context FROM dialogues WHERE translation='' ORDER BY id").fetchall()
    grouped = {}
    for row in rows:
        # A escolha precisa de uma linha única, enquanto diálogos podem ser
        # refluídos. O contexto também separa mensagens dinâmicas, que não
        # podem perder a estrutura interna durante a normalização.
        grouped.setdefault((row["original"], row["kind"], row["context"]), []).append(row["id"])
    items = list(grouped.items())
    completed = 0
    while items:
        batch, chars = [], 0
        while items and len(batch) < config.batch_items:
            (original, kind, context), ids = items[0]
            if batch and chars + len(original) > config.batch_characters:
                break
            items.pop(0); batch.append((original, kind, context, ids)); chars += len(original)
        if should_stop and should_stop():
            break
        started = time.monotonic()
        outputs = translate_batch(config, [item[0] for item in batch])
        for (original, kind, context, ids), text in zip(batch, outputs, strict=True):
            text = core.normalize_text_for_kind(text, kind, context)
            size, width, lines, error, ok = core.validate_text(
                original, text, reject_larger, kind, context
            )
            db.executemany("""UPDATE dialogues SET translation=?,translated_bytes=?,translated_width=?,
                translated_lines=?,size_ok=?,provider=?,error=? WHERE id=?""",
                ((text, size, width, lines, int(ok), config.provider, error, row_id) for row_id in ids))
            completed += len(ids)
        db.commit()
        if progress:
            progress(completed, len(rows))
        elapsed = time.monotonic() - started
        required = 0.25
        time.sleep(max(0, required - elapsed))
    return completed
