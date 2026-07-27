from pathlib import Path

path = Path("tools/parse_gnpy_show_channels_strict.py")
text = path.read_text(encoding="utf-8-sig")

if '"""Strict GNPy parser' in text and 'r"""Strict GNPy parser' not in text:
    text = text.replace('"""Strict GNPy parser', 'r"""Strict GNPy parser', 1)

path.write_text(text, encoding="utf-8")
print("Fixed parser docstring warning.")
