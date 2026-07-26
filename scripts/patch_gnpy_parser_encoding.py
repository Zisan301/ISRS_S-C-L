from pathlib import Path

path = Path("tools/parse_gnpy_show_channels_strict.py")
text = path.read_text(encoding="utf-8-sig")

# Fix warning by making docstring raw.
if text.startswith('"""Strict GNPy parser'):
    text = 'r' + text

old = '''def parse_rows(path: Path):
    clean = re.sub(r"\\x1b\\[[0-9;]*m", "", path.read_text(errors="replace"))
    rows = []
'''

new = '''def read_gnpy_text(path: Path) -> str:
    data = path.read_bytes()

    encodings = ["utf-8-sig", "utf-16", "utf-16-le", "cp1252"]
    for encoding in encodings:
        try:
            text = data.decode(encoding)
            if "The GSNR per channel" in text or "Channel frequency" in text:
                return text
        except UnicodeDecodeError:
            continue

    text = data.decode("utf-8", errors="replace")
    if "\\x00" in text:
        text = text.replace("\\x00", "")
    return text


def parse_rows(path: Path):
    clean = re.sub(r"\\x1b\\[[0-9;]*m", "", read_gnpy_text(path))
    clean = clean.replace("\\x00", "")
    rows = []
'''

if old not in text:
    raise SystemExit("Could not find parse_rows block.")

text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("Patched GNPy parser encoding handling.")