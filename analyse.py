#!/usr/bin/env python3
"""Leest schoolwerk uit de map 'schoolwerk' en maakt eenmalig een compacte werkpunten.md."""
import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIR = ROOT / "schoolwerk"
MODEL = "claude-sonnet-5-5"
MAX_FILES = 10

SUPPORTED_TYPES = {
    ".pdf": "document", ".docx": "docx", ".txt": "text", ".md": "text",
}

PROMPT = """Dit is schoolwerk van een leerling uit het 2de jaar ASO (Vlaanderen): huiswerk en gecorrigeerde toetsen wiskunde.
Maak een heel beknopt, compact overzicht voor haar bijlesleraar (een AI-tutor) met de belangrijkste werkpunten en aandachtspunten, zodat de tutor hiermee kan oefenen. Schrijf in het Nederlands."""


def load_env():
    f = ROOT / ".env"
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def ssl_context():
    try:
        import certifi  # type: ignore
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def extract_docx_text(path):
    try:
        with zipfile.ZipFile(path, "r") as z:
            with z.open("word/document.xml") as f:
                tree = ET.parse(f)
                texts = [node.text for node in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if node.text]
                return "".join(texts)
    except Exception:
        return ""


def main():
    load_env()
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("Zet eerst je API-sleutel in het .env-bestand.")
    
    files = sorted(p for p in DIR.glob("*") if p.suffix.lower() in SUPPORTED_TYPES) if DIR.exists() else []
    if not files:
        sys.exit("Geen ondersteunde bestanden (.pdf, .docx, .txt) gevonden in de map 'schoolwerk'.")
    if len(files) > MAX_FILES:
        files = files[:MAX_FILES]

    content = []
    for p in files:
        suffix = p.suffix.lower()
        file_type = SUPPORTED_TYPES[suffix]
        content.append({"type": "text", "text": f"Bestand: {p.name}"})

        if file_type == "document":
            data = base64.b64encode(p.read_bytes()).decode("ascii")
            content.append({"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}})
        elif file_type == "docx":
            content.append({"type": "text", "text": extract_docx_text(p)})
        elif file_type == "text":
            content.append({"type": "text", "text": p.read_text(encoding="utf-8", errors="ignore")})

    content.append({"type": "text", "text": PROMPT})

    print(f"Bezig met {len(files)} bestand(en) eenmalig analyseren…")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({"model": MODEL, "max_tokens": 1500, "messages": [{"role": "user", "content": content}]}).encode(),
        method="POST",
        headers={"content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120, context=ssl_context()) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        sys.exit(f"Fout bij API-aanroep: {e}")

    text = "\n".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    (ROOT / "werkpunten.md").write_text(text + "\n", encoding="utf-8")
    print("Klaar! Het token-zuinige overzicht staat opgeslagen in werkpunten.md.")


if __name__ == "__main__":
    main()