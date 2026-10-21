from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


FORBIDDEN_SUFFIXES = {".p3a", ".dat", ".tbl", ".ysxproj", ".exe", ".dll"}
FORBIDDEN_NAMES = {"aplicador_ysx.log", ".env"}
SECRET_PATTERNS = {
    "API key": re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9+/=_-]{20,}"),
    "DeepL auth key": re.compile(r"(?i)(?:deepl[_-]?key|authorization)\s*[:=]\s*['\"]?(?:DeepL-Auth-Key\s+)?[A-Za-z0-9:_-]{20,}"),
}


def audit(root: Path) -> list[str]:
    problems: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        relative = path.relative_to(root)
        if path.suffix.lower() in FORBIDDEN_SUFFIXES or path.name.lower() in FORBIDDEN_NAMES:
            problems.append(f"arquivo não publicável: {relative}")
            continue
        if path.stat().st_size > 5_000_000:
            problems.append(f"arquivo inesperadamente grande: {relative}")
        if path.suffix.lower() not in {".py", ".md", ".txt", ".json", ".yml", ".yaml", ".html", ".css", ".js", ".csv", ".spec", ".cs", ""}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            problems.append(f"arquivo de texto não UTF-8: {relative}")
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                problems.append(f"possível segredo ({label}): {relative}")
    return problems


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    findings = audit(target)
    if findings:
        print("Auditoria pública reprovada:")
        for finding in findings:
            print(f"- {finding}")
        raise SystemExit(1)
    print(f"Auditoria pública aprovada: {target}")
