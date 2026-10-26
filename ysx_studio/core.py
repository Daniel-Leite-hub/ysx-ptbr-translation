from __future__ import annotations

import ast
import contextlib
import hashlib
import html
import importlib
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path


TAG_RE = re.compile(r"<[^>]+>")
CONTROL_RE = re.compile(r"<[^>]+>|%(?:\d+\$)?[-+0#]*(?:\d+|\*)?(?:\.\d+)?[diuoxXfFeEgGaAcsp%]")
# Há variantes de escolha que compartilham o mesmo formato de strings, mas
# incluem sufixos de comportamento da interface. Todas precisam entrar no
# catálogo, pois a legenda e a escolha podem reutilizar o mesmo inglês em
# posições diferentes do script.
CALL_RE = re.compile(
    r"system\[(?:5,11|5,4|5,22|15,37|5,20|5,28|5,34)\]\("
    r"|M_SELECTION_(?:CHR|SYS)(?:_(?:VOICE|NO_CURSOR|ENABLE_CANCEL))*\("
    r"|M_(?:MENU_YESNO_OPEN|MENU_3CHOICES_OPEN|ITEM_GET|SHOP|MENU_ADD_ANNOUNCE|BTL_WAVE_PLAY)\("
)
STRING_RE = re.compile(r"(?:(?P<label>\d+)@)?(?P<token>\"(?:\\.|[^\"\\])*\")")
DYNAMIC_MESSAGE_RE = re.compile(r"system\[5,11\].*?\"[^\"]*\"\s*,\s*\d+\s*,\s*\d+\s*,\s*\"", re.S)
PORTUGUESE_TEST = "Ação, coração, informações, água, café, você, avó, último, linguiça."
PORTUGUESE_GLYPHS = "ãõÃÕçÇáéíóúÁÉÍÓÚâêôÂÊÔàÀüÜ"
# A maior escolha original deste jogo ocupa 67 colunas. Diferentemente de um
# diálogo, uma quebra de linha vira outra entrada no balão de seleção.
CHOICE_VISUAL_LIMIT = 67

# Somente campos exibidos ao jogador. Identificadores internos, nomes de assets
# e comandos (por exemplo, obtain_type e diarychr_*) nunca entram no catálogo.
TABLE_TEXT_FIELDS = {
    "t_item.tbl": {
        "ItemTableData": {"name", "short_desc", "long_desc"},
    },
    "t_character_lib.tbl": {
        "CharaLibCategory": {"text"},
        "CharaLibData": {f"text{i}" for i in range(1, 12)},
    },
    "t_adventure_log.tbl": {
        "AdvLogCategoryTab": {"text"},
        "AdvLogMainStory": {"text1", "text2"},
        "AdvLogRecord": {"text1", "text2", "text3"},
    },
    "t_achievement.tbl": {"AchievementTable": {"text1", "text2"}},
    "t_active_voice.tbl": {"ActiveVoiceTable": {"text"}},
    "t_arena.tbl": {"ArenaStage": {"text1"}},
    "t_dialogue.tbl": {"DialogueTable": {"text"}},
    "t_dlc.tbl": {"DLCTable": {"text1", "text2", "text3"}},
    "t_event.tbl": {
        "EventGroupData": {"text"}, "EventSubGroupData": {"text"},
        "EventTable": {"text1", "text2"},
    },
    "t_fast_travel.tbl": {"FastTravelTable": {"alt_travel_point_name", "travel_point_name"}},
    "t_feast.tbl": {"FeastEffectData": {"effect_name"}},
    "t_fugil_letter.tbl": {"FugilLetterData": {"text1", "text2"}},
    "t_help.tbl": {
        "HelpIconList": {"text"}, "HelpImageList": {"text"},
        "HelpPage": {"text1", "text2", "text3"},
    },
    "t_key_config_menu.tbl": {"KeyConfigData": {"text", "toffset"}},
    "t_lookpoint.tbl": {"LookPointTable": {"text"}},
    "t_mana_action_level_up.tbl": {"ManaActionLvUp": {"text1", "text2", "text3"}},
    "t_manaride_game.tbl": {"ManaRideStage": {"text1"}, "ManaRideStageTab": {"text"}},
    "t_map_info.tbl": {
        "MapAreaTable": {"map_name", "text"},
        "MapIslandTable": {"island_name", "island_desc", "text2"},
        "MapSeaTable": {"map_name"},
    },
    "t_map_parts.tbl": {"MapPartsTable": {"text"}},
    "t_minigame_fishing.tbl": {"FishParam": {"text1", "text2"}},
    "t_mission.tbl": {"StoryMissionTable": {"text"}},
    "t_monster_lib.tbl": {"MonsLibData": {"text1", "text2"}},
    "t_name.tbl": {"SNameTable": {"name", "unk_txt_offset"}},
    "t_quest.tbl": {"QuestText": {"text"}, "QuestTitle": {"text"}},
    "t_recapture_island.tbl": {
        "RecaptureIslandInfoTable": {"text1", "text3"},
        "RecaptureIslandMissionTypeTable": {"text1", "text2"},
        "RecaptureIslandSkillTable": {"text1", "text2"},
        "ShipTensionLevelBonusTable": {"text"},
    },
    "t_research.tbl": {"ResearchData": {"observations"}, "ResearchName": {"text"}},
    "t_rune_stone.tbl": {
        "RuneStoneData": {"rune_stone_name", "rune_stone_description", "rune_stone_text"},
    },
    "t_setting_menu.tbl": {"SettingMenuData": {
        "name1", "option_1", "option_1_desc", "option_1_desc_2",
        "option_2", "option_2_desc", "option_2_desc_2",
        "option_3", "option_3_desc", "option_3_desc_2",
        "option_4", "option_4_desc", "option_4_desc_2",
        "option_5", "option_5_desc", "option_5_desc_2",
    }},
    "t_ship_power_up_plan.tbl": {"ShipPowerUpPlan": {
        "name1", "desc_1", "desc_2", "details", "unlock_1", "unlock_2", "unlock_3", "unlock_4",
    }},
    "t_ship_talk.tbl": {"ShipTalkTable": {"text1", "text2"}},
    "t_shop.tbl": {
        "ProductInfo": {"text0"}, "ShopInfo": {"shop_name"}, "ShopNameInfo": {"text1"},
    },
    "t_skill.tbl": {"SSkillTable": {"name", "description_1", "internal_description"}},
    "t_skill_tree_link_bonus.tbl": {"LinkBonusTableData": {
        "ability_name", "ability_name_alt", "simple_desc", "simple_desc_alt",
        "detailed_desc", "detailed_desc_alt",
    }},
    "t_text.tbl": {"TextTableData": {"value"}},
    "t_time_attack.tbl": {"TimeAttackData": {"name1"}},
    "t_time_attack_item.tbl": {"TimeAttackItem": {"name1"}},
    "t_tips.tbl": {"TipsTable": {"text1", "text2", "text3"}},
    "t_topic.tbl": {"TopicTableData": {"text1", "text2"}},
    "t_treasure_map.tbl": {"TreasureMapTable": {"text"}},
}
TABLE_KINDS = {
    "t_item.tbl": "item",
    "t_character_lib.tbl": "personagem/jornal",
    "t_adventure_log.tbl": "jornal",
    "t_active_voice.tbl": "diálogo/voz", "t_dialogue.tbl": "diálogo/voz",
    "t_ship_talk.tbl": "diálogo/voz",
    "t_quest.tbl": "missão/jornal", "t_mission.tbl": "missão/jornal",
    "t_event.tbl": "missão/jornal", "t_topic.tbl": "missão/jornal",
    "t_fugil_letter.tbl": "missão/jornal", "t_rune_stone.tbl": "missão/jornal",
    "t_help.tbl": "interface/ajuda", "t_tips.tbl": "interface/ajuda",
    "t_text.tbl": "interface/ajuda", "t_setting_menu.tbl": "interface/ajuda",
    "t_key_config_menu.tbl": "interface/ajuda",
    "t_monster_lib.tbl": "bestiário", "t_research.tbl": "bestiário",
    "t_map_info.tbl": "mapa", "t_map_parts.tbl": "mapa",
    "t_fast_travel.tbl": "mapa", "t_lookpoint.tbl": "mapa",
    "t_treasure_map.tbl": "mapa",
    "t_skill.tbl": "habilidade", "t_skill_tree_link_bonus.tbl": "habilidade",
    "t_mana_action_level_up.tbl": "habilidade",
}

# Tags editoriais são independentes das tags/comandos internos do jogo. Elas
# servem apenas para localizar grupos de texto no Studio e no CSV exportado.
# Um mesmo texto pode pertencer a várias categorias (por exemplo: uma
# descrição de habilidade recebe ``habilidades`` e ``descricoes``).
TAG_LABELS = {
    "cinematicas": "Cinemáticas/legendas",
    "dialogos": "Diálogos", "vozes": "Vozes", "escolhas": "Escolhas",
    "menus": "Menus", "interface": "Interface", "sistema": "Sistema/avisos",
    "notificacoes": "Notificações", "itens": "Itens", "habilidades": "Habilidades",
    "descricoes": "Descrições", "nomes": "Nomes/títulos", "tutoriais": "Tutoriais/ajuda",
    "missoes": "Missões", "eventos": "Eventos", "diario": "Diário/jornal",
    "perfis": "Perfis", "personagens": "Personagens", "bestiario": "Bestiário",
    "mapas": "Mapas", "viagem-rapida": "Viagem rápida", "tesouros": "Mapas do tesouro",
    "lojas": "Lojas", "navio": "Navio", "melhorias": "Melhorias",
    "conquistas": "Conquistas", "dlc": "DLC", "minijogos": "Minijogos",
    "arena": "Arena", "pesca": "Pesca", "mana-ride": "Mana Ride",
    "cartas": "Cartas", "runas": "Pedras rúnicas", "configuracoes": "Configurações",
    "controles": "Controles", "culinaria": "Refeições/culinária", "recaptura": "Recaptura de ilhas",
}

TABLE_CONTENT_TAGS = {
    "t_item.tbl": {"itens"},
    "t_character_lib.tbl": {"perfis", "personagens", "diario"},
    "t_adventure_log.tbl": {"diario", "eventos"},
    "t_achievement.tbl": {"conquistas"},
    "t_active_voice.tbl": {"dialogos", "vozes"},
    "t_arena.tbl": {"minijogos", "arena"},
    "t_dialogue.tbl": {"dialogos", "vozes"},
    "t_dlc.tbl": {"dlc", "itens"},
    "t_event.tbl": {"eventos", "missoes", "diario"},
    "t_fast_travel.tbl": {"mapas", "viagem-rapida"},
    "t_feast.tbl": {"culinaria"},
    "t_fugil_letter.tbl": {"cartas", "diario"},
    "t_help.tbl": {"tutoriais", "interface"},
    "t_key_config_menu.tbl": {"menus", "controles", "configuracoes"},
    "t_lookpoint.tbl": {"mapas"},
    "t_mana_action_level_up.tbl": {"habilidades"},
    "t_manaride_game.tbl": {"minijogos", "mana-ride"},
    "t_map_info.tbl": {"mapas"}, "t_map_parts.tbl": {"mapas"},
    "t_minigame_fishing.tbl": {"minijogos", "pesca"},
    "t_mission.tbl": {"missoes"},
    "t_monster_lib.tbl": {"bestiario"},
    "t_name.tbl": {"nomes", "personagens"},
    "t_quest.tbl": {"missoes", "diario"},
    "t_recapture_island.tbl": {"recaptura", "missoes"},
    "t_research.tbl": {"bestiario"},
    "t_rune_stone.tbl": {"runas", "diario"},
    "t_setting_menu.tbl": {"menus", "configuracoes", "interface"},
    "t_ship_power_up_plan.tbl": {"navio", "melhorias"},
    "t_ship_talk.tbl": {"dialogos", "vozes", "navio"},
    "t_shop.tbl": {"lojas", "menus"},
    "t_skill.tbl": {"habilidades"},
    "t_skill_tree_link_bonus.tbl": {"habilidades", "melhorias"},
    "t_text.tbl": {"interface", "menus"},
    "t_time_attack.tbl": {"minijogos"}, "t_time_attack_item.tbl": {"minijogos", "itens"},
    "t_tips.tbl": {"tutoriais", "interface"},
    "t_topic.tbl": {"eventos", "diario"},
    "t_treasure_map.tbl": {"mapas", "tesouros"},
}

TAG_ALIASES = {
    "dialogo": "dialogos", "voz": "vozes", "escolha": "escolhas", "menu": "menus",
    "item": "itens", "habilidade": "habilidades", "descricao": "descricoes",
    "tutorial": "tutoriais", "ajuda": "tutoriais", "missao": "missoes",
    "perfil": "perfis", "personagem": "personagens", "jornal": "diario",
    "mapa": "mapas", "loja": "lojas", "conquista": "conquistas",
    "minijogo": "minijogos", "notificacao": "notificacoes",
    "configuracao": "configuracoes", "controle": "controles", "runa": "runas",
}


def normalize_content_tag(value: str) -> str:
    """Normaliza uma tag digitada, aceitando acentos, singular e plural."""
    folded = unicodedata.normalize("NFKD", value.strip().casefold())
    slug = "".join(char for char in folded if not unicodedata.combining(char))
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return TAG_ALIASES.get(slug, slug)


def content_tags(file_name: str, kind: str, context: str = "") -> tuple[str, ...]:
    """Retorna tags de busca editoriais derivadas da origem e do campo."""
    tags: set[str] = set()
    kind_tags = {
        "diálogo": {"dialogos"}, "diálogo/voz": {"dialogos", "vozes"},
        "legenda/cinemática": {"dialogos", "vozes", "cinematicas"},
        "escolha": {"escolhas", "menus"}, "texto de sistema": {"sistema", "interface"},
        "item": {"itens"}, "habilidade": {"habilidades"},
        "interface/ajuda": {"interface"}, "missão/jornal": {"missoes", "diario"},
        "jornal": {"diario"}, "personagem/jornal": {"perfis", "personagens", "diario"},
        "bestiário": {"bestiario"}, "mapa": {"mapas"}, "sistema/jogo": {"sistema"},
    }
    tags.update(kind_tags.get(kind, ()))
    if context.startswith("ResearchData"):
        locator = _table_locator(context)
        if locator.get("field") == "profile":
            tags.update(("perfis", "descricoes", "diario"))
        elif locator.get("field") == "imressions":
            tags.update(("dialogos", "diario"))
    table_name = Path(file_name).name if file_name.startswith("table_eng/") else ""
    tags.update(TABLE_CONTENT_TAGS.get(table_name, ()))

    field_match = re.search(r"campo ([^\s]+)", context)
    field = field_match.group(1).casefold() if field_match else ""
    if any(marker in field for marker in ("desc", "details", "observations")):
        tags.add("descricoes")
    if any(marker in field for marker in ("name", "title")) or field == "text1" and table_name in {
        "t_achievement.tbl", "t_adventure_log.tbl", "t_help.tbl", "t_quest.tbl",
        "t_skill.tbl", "t_topic.tbl",
    }:
        tags.add("nomes")
    if table_name == "t_character_lib.tbl" and field != "text1" and "CharaLibData" in context:
        tags.add("descricoes")
    if table_name in {"t_help.tbl", "t_tips.tbl"} and field in {"text2", "text3"}:
        tags.add("descricoes")

    lowered_file, lowered_context = file_name.casefold(), context.casefold()
    if not table_name:
        if "sys_shop" in lowered_file or "m_shop" in lowered_context:
            tags.update(("lojas", "menus"))
        if "m_menu_" in lowered_context or lowered_file in {"system.ing", "title.ing"}:
            tags.add("menus")
        if "m_item_get" in lowered_context or lowered_file == "item.ing":
            tags.update(("itens", "notificacoes"))
        if "recapture" in lowered_file:
            tags.update(("recaptura", "missoes"))
        if re.search(r"system\[(?:5,4|5,20|5,28|5,34|15,37)\]", lowered_context):
            tags.add("notificacoes")

    order = {tag: index for index, tag in enumerate(TAG_LABELS)}
    return tuple(sorted(tags, key=lambda tag: (order.get(tag, 999), tag)))
_KURO_LOCK = threading.Lock()


class StudioError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExtractedText:
    file_name: str
    kind: str
    source_start: int
    source_end: int
    original: str
    original_bytes: int
    original_width: int
    original_lines: int
    tags: str
    context: str


def resource_path(*parts: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return root.joinpath(*parts)


def find_tool(name: str, game_dir: Path | None = None) -> Path:
    candidates = [resource_path("tools", name), resource_path(name)]
    if game_dir:
        candidates.append(game_dir / name)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise StudioError(f"Ferramenta necessária não encontrada: {name}")


def font_support_report(game_dir: Path) -> dict[str, bool]:
    font = game_dir / "asset" / "common" / "font" / "font_mes_eng.fnt"
    if not font.is_file():
        archive = game_dir / "misc.p3a"
        if not archive.is_file():
            raise StudioError("Não encontrei font_mes_eng.fnt nem misc.p3a.")
        p3a = find_tool("p3a_tool.exe", game_dir)
        run_tool([str(p3a), "extract", str(archive)], cwd=game_dir)
    data = font.read_bytes()
    table = data.find(b"FLTI")
    if data[:4] != b"FCV\0" or table < 0:
        raise StudioError("Tabela de fonte FCV/FLTI não reconhecida.")
    size = struct.unpack_from("<I", data, table + 4)[0]
    start = table + 8
    if size % 24 or start + size > len(data):
        raise StudioError("Tabela de glifos da fonte está inconsistente.")
    codepoints = {struct.unpack_from("<I", data, offset)[0] for offset in range(start, start + size, 24)}
    return {char: ord(char) in codepoints for char in PORTUGUESE_GLYPHS}


def run_tool(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(args, cwd=cwd, text=True, encoding="utf-8", errors="replace",
                            capture_output=True, creationflags=flags)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise StudioError(detail[-2000:] or f"Falha ao executar {Path(args[0]).name}")
    return result


def decompile_scripts(game_dir: Path, output_dir: Path, progress=None) -> list[Path]:
    source = game_dir / "script_eng" / "scena"
    if not source.is_dir():
        archive = game_dir / "script.p3a"
        if not archive.is_file():
            raise StudioError("Não encontrei script_eng\\scena nem script.p3a nesta pasta.")
        if progress:
            progress(0, 1, "Extraindo script.p3a (uma vez)...")
        p3a = find_tool("p3a_tool.exe", game_dir)
        run_tool([str(p3a), "extract", str(archive)], cwd=game_dir)
    if not source.is_dir():
        raise StudioError("O pacote foi extraído, mas script_eng\\scena não foi localizado.")
    ingert = find_tool("ingert.exe", game_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(path for path in source.glob("*.dat")
                   if path.stem != "debug" and not path.stem.startswith(("test", "sample")))
    for index, path in enumerate(files, 1):
        destination = output_dir / f"{path.stem}.ing"
        run_tool([str(ingert), str(path), "--roundtrip", "-o", str(destination)])
        if progress:
            progress(index, len(files), path.name)
    return sorted(output_dir.glob("*.ing"))


def _call_end(source: str, open_paren: int) -> int:
    depth, quoted, escaped = 0, False, False
    for pos in range(open_paren, len(source)):
        char = source[pos]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return pos + 1
    raise StudioError("Chamada de script sem fechamento")


def _decode(token: str) -> str:
    try:
        return ast.literal_eval(token)
    except (SyntaxError, ValueError) as exc:
        raise StudioError(f"String inválida no script: {token[:80]}") from exc


def visible_width(text: str) -> int:
    visible = TAG_RE.sub("", text)
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in visible)


DICAS_VISUAL_LIMIT = 49
MISSOES_VISUAL_LIMIT = 56
MAP_ISLAND_DESC_VISUAL_LIMIT = 45


def is_tip_body(context: str) -> bool:
    """Identifica somente o corpo das dicas, não títulos ou textos de menu.

    O limite de 49 colunas foi calibrado visualmente a partir de uma linha
    que cabe no quadro de dicas, preservando a margem horizontal do painel.
    """
    return "TipsTable" in (context or "") and '"field":"text3"' in context


def is_quest_body(context: str) -> bool:
    """Identifica a descrição mostrada no quadro de aceite de missão.

    O limite de 56 colunas foi calibrado pelas capturas do painel: 72 colunas
    ultrapassam a margem direita, enquanto 56 preservam a área útil do quadro.
    """
    return "QuestText" in (context or "") and '"field":"text"' in context


def is_map_island_description(context: str) -> bool:
    """Identifica a descrição exibida no quadro de informações da ilha."""
    return "MapIslandTable" in (context or "") and '"field":"island_desc"' in context


def is_item_single_line_field(context: str) -> bool:
    """Identifica nome, efeito e descrição desenhados no painel de itens.

    O jogo não aumenta o espaçamento vertical quando esses campos contêm uma
    quebra explícita; a segunda linha é desenhada sobre o campo seguinte.
    """
    value = context or ""
    return "ItemTableData" in value and any(
        f'"field":"{field}"' in value for field in ("name", "short_desc", "long_desc")
    )


def wrap_visual_lines(text: str, limit: int = 72, reflow: bool = True) -> str:
    """Quebra por palavras; no modo reflow, elimina quebras prematuras.

    Assim a linha 2 só começa após a primeira atingir o limite e a linha 3 só
    existe quando a segunda realmente transborda. Quebras já existentes são
    tratadas como espaços no texto de diálogo.
    """
    if limit < 1:
        raise ValueError("O limite visual deve ser positivo")
    if reflow:
        text = re.sub(r"[\t\r\n ]+", " ", text).strip(" ")
    wrapped_lines: list[str] = []
    for source_line in text.split("\n"):
        if visible_width(source_line) <= limit:
            wrapped_lines.append(source_line)
            continue
        current = ""
        spacing = ""
        for part in re.findall(r"\s+|\S+", source_line):
            if part.isspace():
                spacing += part
                continue
            candidate = current + spacing + part
            if current and visible_width(candidate) > limit:
                wrapped_lines.append(current)
                current = part
            else:
                current = candidate
            spacing = ""
        wrapped_lines.append(current + spacing)
    return "\n".join(wrapped_lines)


def normalize_text_for_kind(text: str, kind: str, context: str = "") -> str:
    """Aplica a regra de layout apropriada ao tipo de texto do jogo.

    Escolhas não podem ser refluídas: uma nova linha é renderizada pelo jogo
    como outro balão. Elas permanecem em uma linha para que a validação possa
    pedir uma redação menor quando ultrapassarem o limite próprio.
    """
    if is_research_panel_line(context):
        return re.sub(r"[\t\r\n ]+", " ", text).strip(" ")
    if kind == "legenda/cinemática":
        return text.replace("\r\n", "\n")
    if kind == "escolha":
        return re.sub(r"[\t\r\n ]+", " ", text).strip(" ")
    if is_item_single_line_field(context):
        return re.sub(r"[\t\r\n ]+", " ", text).strip(" ")
    if is_tip_body(context):
        return wrap_visual_lines(text, limit=DICAS_VISUAL_LIMIT, reflow=True)
    if is_quest_body(context):
        return wrap_visual_lines(text, limit=MISSOES_VISUAL_LIMIT, reflow=True)
    if is_map_island_description(context):
        # As quebras são ajustadas com base no número de linhas do original.
        # Preserve-as ao salvar e limite apenas eventuais linhas longas.
        return wrap_visual_lines(text, limit=MAP_ISLAND_DESC_VISUAL_LIMIT, reflow=False)
    reflow = kind in {"diálogo", "diálogo/voz"} and not requires_dynamic_segment(context)
    return wrap_visual_lines(text, reflow=reflow)


def text_metrics(text: str) -> tuple[int, int, int]:
    # split("\n") mantém uma linha vazia final, relevante para layout e reinserção.
    lines = text.split("\n")
    return len(text.encode("utf-8")), max(map(visible_width, lines), default=0), len(lines)


def tags_signature(text: str) -> str:
    return json.dumps(CONTROL_RE.findall(text), ensure_ascii=False)


def requires_dynamic_segment(context: str) -> bool:
    """Indica mensagem que intercala duas strings com ID/argumento do jogo."""
    return bool(DYNAMIC_MESSAGE_RE.search(context or ""))


def _kurotools_root() -> Path:
    candidates = [
        resource_path("kurotools"),
        Path(__file__).resolve().parents[1] / ".vendor" / "KuroTools",
        Path(__file__).resolve().parents[2] / ".vendor" / "KuroTools",
    ]
    for candidate in candidates:
        if (candidate / "tbl2json.py").is_file() and (candidate / "schemas").is_dir():
            return candidate
    raise StudioError("Conversor de tabelas KuroTools não foi encontrado no pacote.")


@contextlib.contextmanager
def _working_directory(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _kuro_modules():
    root = _kurotools_root()
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    # As tabelas oficiais usadas aqui não são criptografadas. Este módulo
    # externo tenta instalar zstandard ao importar; a implementação mínima
    # evita rede/pip dentro do EXE e mantém o caminho seguro para #TBL.
    if "processcle" not in sys.modules:
        import types
        processcle = types.ModuleType("processcle")
        processcle.processCLE = lambda data: data
        sys.modules["processcle"] = processcle
    return root, importlib.import_module("tbl2json"), importlib.import_module("json2tbl")


def decompile_tables(game_dir: Path, output_dir: Path, progress=None) -> list[Path]:
    game_dir = game_dir.resolve()
    output_dir = output_dir.resolve()
    source = game_dir / "table_eng"
    if not source.is_dir():
        raise StudioError("Não encontrei a pasta table_eng com itens e diário.")
    output_dir.mkdir(parents=True, exist_ok=True)
    result: list[Path] = []
    root, tbl2json, _json2tbl = _kuro_modules()
    names = list(TABLE_TEXT_FIELDS)
    with _KURO_LOCK, _working_directory(root):
        for index, name in enumerate(names, 1):
            table = source / name
            if not table.is_file():
                continue
            generated = root / f"{table.stem}.json"
            with contextlib.redirect_stdout(io.StringIO()):
                tbl2json.parse(table, game="Ys_X_Proud")
            destination = output_dir / generated.name
            shutil.move(generated, destination)
            result.append(destination)
            if progress:
                progress(index, len(names), f"Catalogando {name}")
    return result


def extract_table_json(path: Path) -> list[ExtractedText]:
    table_name = f"{path.stem}.tbl"
    allowed = TABLE_TEXT_FIELDS.get(table_name, {})
    document = json.loads(path.read_text(encoding="utf-8"))
    rows: list[ExtractedText] = []
    serial = 0
    for section in document.get("data", []):
        section_name = section.get("name", "")
        fields = allowed.get(section_name, set())
        for row_index, record in enumerate(section.get("data", [])):
            identity = record.get("id", record.get("uint1", row_index))
            for field_index, field in enumerate(sorted(fields)):
                value = record.get(field)
                if not isinstance(value, str) or not value.strip():
                    continue
                serial += 1
                byte_count, width, lines = text_metrics(value)
                locator = json.dumps({"section": section_name, "index": row_index, "field": field},
                                     ensure_ascii=False, separators=(",", ":"))
                kind = TABLE_KINDS.get(table_name, "sistema/jogo")
                rows.append(ExtractedText(
                    f"table_eng/{table_name}", kind, serial, serial + 1, value,
                    byte_count, width, lines, tags_signature(value),
                    f"{section_name} · registro {identity} · campo {field}\n{locator}",
                ))
    # Append nested fields after all historical scalar fields so existing
    # source_start identities and translations are never renumbered.
    if table_name == "t_research.tbl":
        for section in document.get("data", []):
            if section.get("name") != "ResearchData":
                continue
            for index, record in enumerate(section["data"]):
                for field, leaf in (("profile", "type"), ("imressions", "text")):
                    for child_index, child in enumerate(record.get(field, [])):
                        value = child.get(leaf)
                        if not isinstance(value, str) or not value.strip():
                            continue
                        serial += 1
                        size, width, lines = text_metrics(value)
                        locator = {"section": "ResearchData", "index": index, "field": field,
                                   "path": [child_index, leaf]}
                        if field == "imressions":
                            locator["speaker_id"] = child.get("character_id")
                        rows.append(ExtractedText(
                            "table_eng/t_research.tbl", "bestiário", serial, serial+1, value,
                            size, width, lines, tags_signature(value),
                            f"ResearchData · registro {index} · campo {field}/{child_index}/{leaf}\n"
                            + json.dumps(locator,ensure_ascii=False,separators=(",", ":"))))
    return rows


def is_research_panel_line(context: str) -> bool:
    if not context.startswith("ResearchData"):
        return False
    locator = _table_locator(context)
    return locator.get("field") in {"profile", "imressions"} and bool(locator.get("path"))


def _table_locator(context: str) -> dict:
    try:
        return json.loads(context.rsplit("\n", 1)[-1])
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise StudioError("Localizador de tabela inválido no projeto.") from exc


def compile_tables(original_dir: Path, output_dir: Path,
                   rows_by_file: dict[str, list[dict]]) -> list[Path]:
    original_dir = original_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    root, _tbl2json, json2tbl = _kuro_modules()
    compiled: list[Path] = []
    with _KURO_LOCK, _working_directory(root):
        for file_name, rows in rows_by_file.items():
            stem = Path(file_name).stem
            source_json = original_dir / f"{stem}.json"
            if not source_json.is_file():
                raise StudioError(f"Fonte JSON da tabela não encontrada: {source_json.name}")
            document = json.loads(source_json.read_text(encoding="utf-8"))
            sections = {section["name"]: section["data"] for section in document["data"]}
            for row in rows:
                final = row["reviewed"] or row["translation"]
                if not final:
                    continue
                locator = _table_locator(row["context"])
                target = sections[locator["section"]][locator["index"]]
                keys = [locator["field"], *locator.get("path", [])]
                for key in keys[:-1]:
                    target = target[key]
                if target[keys[-1]] != row["original"]:
                    raise StudioError("Fonte de tabela alterada; tradução exige reconciliação.")
                target[keys[-1]] = final
            staging_json = root / f"{stem}.json"
            staging_json.write_text(json.dumps(document, ensure_ascii=False, indent="\t"), encoding="utf-8")
            try:
                json2tbl.pack(staging_json)
                generated = root / f"{stem}.tbl"
                destination = output_dir / generated.name
                shutil.move(generated, destination)
                compiled.append(destination)
            finally:
                if staging_json.exists():
                    staging_json.unlink()
    return compiled


def validate_text(original: str, candidate: str, reject_larger: bool = False,
                  kind: str = "", context: str = "") -> tuple[int, int, int, str, bool]:
    byte_count, width, lines = text_metrics(candidate)
    original_bytes, original_width, original_lines = text_metrics(original)
    if tags_signature(original) != tags_signature(candidate):
        return byte_count, width, lines, "Tags/comandos internos foram alterados", False
    if "\x00" in candidate:
        return byte_count, width, lines, "O texto contém byte nulo", False
    if reject_larger and byte_count > original_bytes:
        return byte_count, width, lines, "Texto maior que o original (política estrita)", False
    if is_research_panel_line(context):
        if lines != 1:
            return byte_count, width, lines, "Perfil/impressão da pesquisa deve ocupar uma linha", False
        if width > max(72, original_width):
            return byte_count, width, lines, "Texto excede orçamento conservador do painel de pesquisa", False
        return byte_count, width, lines, "", True
    if kind == "legenda/cinemática":
        if lines != original_lines:
            return byte_count, width, lines, "Preserve o número de segmentos da legenda original", False
        if any(tags_signature(a) != tags_signature(b)
               for a, b in zip(original.split("\n"), candidate.split("\n"), strict=True)):
            return byte_count, width, lines, "Preserve os comandos em seus segmentos originais", False
        # Conservative editorial budget, not a measured pixel/font limit.
        if width > max(72, original_width):
            return byte_count, width, lines, "Legenda excede o orçamento conservador de largura", False
        return byte_count, width, lines, "", True
    if kind == "escolha":
        if lines > 1:
            return byte_count, width, lines, (
                f"Escolha ocupa {lines} linhas; o balão aceita apenas 1 linha"
            ), False
        if width > CHOICE_VISUAL_LIMIT:
            return byte_count, width, lines, (
                f"Escolha com {width} colunas; limite do balão {CHOICE_VISUAL_LIMIT}"
            ), False
    if is_item_single_line_field(context):
        if lines > 1:
            return byte_count, width, lines, (
                f"Campo de item ocupa {lines} linhas; o painel aceita somente 1"
            ), False
        # A largura útil varia entre nome, efeito e descrição. Neste modo de
        # teste, a prioridade é eliminar a quebra que provoca sobreposição.
        return byte_count, width, lines, "", True
    if is_tip_body(context):
        if width > DICAS_VISUAL_LIMIT:
            return byte_count, width, lines, (
                f"Linha com {width} colunas; limite visual das dicas {DICAS_VISUAL_LIMIT}"
            ), False
        # A altura das dicas é dinâmica; não rejeite uma linha adicional após
        # a quebra por palavra, pois isso recriaria o estouro horizontal.
        return byte_count, width, lines, "", True
    if is_quest_body(context):
        if width > MISSOES_VISUAL_LIMIT:
            return byte_count, width, lines, (
                f"Linha com {width} colunas; limite visual das missões {MISSOES_VISUAL_LIMIT}"
            ), False
        # O painel cresce verticalmente dentro do quadro; prioriza-se impedir
        # o estouro horizontal, que é o defeito visível neste tipo de texto.
        return byte_count, width, lines, "", True
    if is_map_island_description(context):
        if width > MAP_ISLAND_DESC_VISUAL_LIMIT:
            return byte_count, width, lines, (
                f"Linha com {width} colunas; limite visual das descrições do mapa "
                f"{MAP_ISLAND_DESC_VISUAL_LIMIT}"
            ), False
        if lines > max(3, original_lines):
            return byte_count, width, lines, (
                f"{lines} linhas; o quadro da descrição aceita até {max(3, original_lines)}"
            ), False
        return byte_count, width, lines, "", True
    max_width = 72
    max_lines = max(3, original_lines)
    if width > max_width:
        return byte_count, width, lines, f"Linha com {width} colunas; limite visual {max_width}", False
    if lines > max_lines:
        return byte_count, width, lines, f"{lines} linhas; limite visual {max_lines}", False
    return byte_count, width, lines, "", True


def extract_file(path: Path) -> list[ExtractedText]:
    if path.suffix.lower() == ".maya_scene":
        from .cinematics import extract
        return extract(path)
    source = path.read_text(encoding="utf-8")
    rows: list[ExtractedText] = []
    for call_match in CALL_RE.finditer(source):
        line_start = source.rfind("\n", 0, call_match.start()) + 1
        if source[line_start:call_match.start()].lstrip().startswith("prelude fn"):
            continue
        call_end = _call_end(source, call_match.end() - 1)
        call = source[call_match.start():call_end]
        strings = []
        for match in STRING_RE.finditer(call):
            value = _decode(match.group("token"))
            if value and TAG_RE.sub("", value).strip():
                absolute_start = call_match.start() + match.start()
                absolute_end = call_match.start() + match.end()
                strings.append((absolute_start, absolute_end, value))
        if not strings:
            continue
        is_message = call.startswith("system[5,11]")
        is_selection = call.startswith("M_SELECTION_")
        if is_message:
            # Mantém os offsets históricos do catálogo de diálogos.
            groups = [strings]
        elif is_selection:
            groups = [[item] for item in strings]
        else:
            # Outros componentes visuais podem intercalar texto com variáveis,
            # IDs de item ou números. Só una strings quando o separador for o
            # marcador explícito de nova linha `10`; assim o build nunca remove
            # conteúdo dinâmico do comando.
            groups = []
            current = []
            for item in strings:
                visible = html.unescape(TAG_RE.sub("", item[2])).strip()
                asset_like = bool(re.fullmatch(r"[a-z][a-z0-9_./\\-]*", visible))
                if not visible or not any(char.isalpha() for char in visible) or asset_like:
                    if current:
                        groups.append(current); current = []
                    continue
                if current:
                    separator = source[current[-1][1]:item[0]]
                    if not re.fullmatch(r"\s*,\s*10\s*,\s*", separator):
                        groups.append(current); current = []
                current.append(item)
            if current:
                groups.append(current)
        kind = (
            "diálogo" if is_message else
            "escolha" if is_selection or call.startswith("M_MENU_") else
            "diálogo/voz" if call.startswith("system[5,22]") else
            "texto de sistema"
        )
        for group in groups:
            original = "\n".join(item[2] for item in group)
            byte_count, width, lines = text_metrics(original)
            context_start = source.rfind("\n", 0, max(0, line_start - 1)) + 1
            context_end = source.find("\n", call_end)
            context = source[context_start: context_end if context_end >= 0 else call_end].strip()
            rows.append(ExtractedText(
                path.name, kind,
                group[0][0], group[-1][1], original, byte_count, width, lines,
                tags_signature(original), context[:800],
            ))
    return rows


def quote_ingert(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def replacement_expression(text: str) -> str:
    lines = text.split("\n")
    return ", 10, ".join(quote_ingert(line) for line in lines)


def replacement_preserving_dynamic(segment: str, text: str) -> str:
    """Troca somente as strings de uma mensagem, preservando argumentos."""
    matches = list(STRING_RE.finditer(segment))
    lines = text.split("\n")
    if len(matches) < 2 or len(lines) != len(matches):
        return replacement_expression(text)
    pieces, cursor = [], 0
    for match, line in zip(matches, lines, strict=True):
        pieces.append(segment[cursor:match.start()])
        pieces.append(quote_ingert(line))
        cursor = match.end()
    pieces.append(segment[cursor:])
    return "".join(pieces)


def build_sources(decompiled_dir: Path, build_source_dir: Path, rows_by_file: dict[str, list[dict]]) -> list[Path]:
    if build_source_dir.exists():
        shutil.rmtree(build_source_dir)
    shutil.copytree(decompiled_dir, build_source_dir)
    changed: list[Path] = []
    for file_name, rows in rows_by_file.items():
        path = build_source_dir / file_name
        if path.suffix.lower() == ".maya_scene":
            from . import cinematics
            document = cinematics.patch(cinematics.load(path), rows)
            path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
            changed.append(path)
            continue
        source = path.read_text(encoding="utf-8")
        for row in sorted(rows, key=lambda item: item["source_start"], reverse=True):
            # Preserva o texto escolhido byte a byte, inclusive espaços e quebras intencionais.
            final = wrap_visual_lines(
                row["reviewed"] or row["translation"],
                reflow=not requires_dynamic_segment(row.get("context", "")),
            )
            if not final:
                continue
            segment = source[row["source_start"]:row["source_end"]]
            replacement = (replacement_preserving_dynamic(segment, final)
                           if requires_dynamic_segment(row.get("context", ""))
                           else replacement_expression(final))
            source = source[:row["source_start"]] + replacement + source[row["source_end"]:]
        path.write_text(source, encoding="utf-8", newline="\n")
        changed.append(path)
    return changed


def compile_mod(game_dir: Path, build_source_dir: Path, output_dir: Path, files: list[Path],
                table_files: list[Path] | None = None, progress=None) -> Path:
    ingert = find_tool("ingert.exe", game_dir)
    p3a = find_tool("p3a_tool.exe", game_dir)
    loose_root = output_dir / "loose"
    scena_dir = loose_root / "script_eng" / "scena"
    if loose_root.exists():
        shutil.rmtree(loose_root)
    scena_dir.mkdir(parents=True)
    has_cinematics = False
    for index, source in enumerate(files, 1):
        if source.suffix.lower() == ".maya_scene":
            destination = loose_root / "maya_scene_eng" / source.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            has_cinematics = True
            if progress:
                progress(index, len(files), source.name)
            continue
        relative = source.relative_to(build_source_dir)
        if relative.parts and relative.parts[0].lower() == "ani":
            destination = loose_root / "script_eng" / "ani" / f"{source.stem}.dat"
            destination.parent.mkdir(parents=True, exist_ok=True)
            verify_path = output_dir / "verify" / "ani" / f"{source.stem}.ing"
        else:
            destination = scena_dir / f"{source.stem}.dat"
            verify_path = output_dir / "verify" / f"{source.stem}.ing"
        run_tool([str(ingert), str(source), "-o", str(destination)])
        # Compilation followed by decompilation is a practical structural check.
        verify_path.parent.mkdir(parents=True, exist_ok=True)
        run_tool([str(ingert), str(destination), "--roundtrip", "-o", str(verify_path)])
        if progress:
            progress(index, len(files), source.name)
    packaged_roots = ["script_eng"]
    if has_cinematics:
        packaged_roots.append("maya_scene_eng")
    if table_files:
        table_dir = loose_root / "table_eng"
        table_dir.mkdir(parents=True, exist_ok=True)
        for table in table_files:
            shutil.copy2(table, table_dir / table.name)
        packaged_roots.append("table_eng")
    archive = (output_dir / "zzz_ysx_ptbr.p3a").resolve()
    if archive.exists():
        archive.unlink()
    run_tool([str(p3a), "archive", str(archive), *packaged_roots, "--comp=auto"], cwd=loose_root)
    return archive


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
