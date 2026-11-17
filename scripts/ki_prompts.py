"""Schreibt alle Prompts aus den Claude-Code-Sitzungen dieses Projekts nach
docs/KI-Prompts.md (für die KI-Deklaration, Projektbeschreibung S. 4).

Claude Code speichert jede Sitzung als JSONL unter
~/.claude/projects/<Projektpfad>/. Das Skript liest nur die Eingaben der
Person (keine Antworten, keine Tool-Ausgaben) und hängt nichts an,
sondern schreibt die Datei jedes Mal vollständig neu.

    python scripts/ki_prompts.py
    python scripts/ki_prompts.py --sitzungen <Ordner> --autor "Luca"

Jedes Teammitglied führt es auf dem eigenen Rechner aus; die Dateien
werden mit --ausgabe getrennt abgelegt.
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INTERNE_TAGS = (
    "system-reminder",
    "ide_opened_file",
    "ide_selection",
    "local-command-caveat",
    "local-command-stdout",
    "command-message",
    "command-args",
    "task-notification",
)
TAG = re.compile(rf"<({'|'.join(INTERNE_TAGS)})>.*?</\1>", re.S)
EINGEFUEGT = re.compile(r"<pasted_content[^>]*>(.*?)</pasted_content>", re.S)


def standard_ordner() -> Path:
    name = re.sub(r"[^A-Za-z0-9]", "-", str(ROOT))
    return Path.home() / ".claude" / "projects" / name


def prompts(ordner: Path) -> list[tuple[str, str, str]]:
    eintraege = []
    for datei in sorted(ordner.glob("*.jsonl")):
        for zeile in datei.open(encoding="utf-8"):
            try:
                daten = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            if daten.get("type") != "user" or daten.get("isMeta") or daten.get("isCompactSummary"):
                continue
            inhalt = daten.get("message", {}).get("content")
            anhang = False
            if isinstance(inhalt, list):
                if any(b.get("type") == "tool_result" for b in inhalt):
                    continue
                anhang = any(b.get("type") in ("image", "document") for b in inhalt)
                inhalt = "\n".join(b.get("text", "") for b in inhalt if b.get("type") == "text")
            if not isinstance(inhalt, str):
                continue
            text = TAG.sub("", inhalt)
            text = re.sub(r"<command-name>(.*?)</command-name>", r"\1", text)
            text = EINGEFUEGT.sub(r"[eingefügter Text]\n\1", text).strip()
            if not text or text.startswith("This session is being continued") or text == "/compact":
                continue
            if anhang:
                text += "\n[Anhang: Bild/PDF]"
            zeit = daten.get("timestamp", "")[:16].replace("T", " ")
            eintraege.append((zeit, datei.stem[:8], text))
    return sorted(eintraege)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sitzungen", type=Path, default=standard_ordner())
    parser.add_argument("--ausgabe", type=Path, default=ROOT / "docs" / "KI-Prompts.md")
    parser.add_argument("--autor", default="Elias")
    args = parser.parse_args()
    if not args.sitzungen.exists():
        parser.error(f"Ordner fehlt: {args.sitzungen}")
    eintraege = prompts(args.sitzungen)
    zeilen = [
        f"# KI-Prompts ({args.autor})",
        "",
        "Automatisch erzeugt mit `python scripts/ki_prompts.py` aus den Claude-Code-Sitzungen. "
        "Werkzeug: Claude Code (Anthropic). Zeiten in UTC. Zusammenfassung und Einordnung: "
        "[KI-Deklaration.md](KI-Deklaration.md).",
        "",
    ]
    for zeit, sitzung, text in eintraege:
        zeilen += [f"### {zeit} · Sitzung {sitzung}", "", "```text", text, "```", ""]
    args.ausgabe.parent.mkdir(parents=True, exist_ok=True)
    args.ausgabe.write_text("\n".join(zeilen), encoding="utf-8")
    print(f"{len(eintraege)} Prompts -> {args.ausgabe}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
