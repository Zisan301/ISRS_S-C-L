from pathlib import Path

path = Path("tests/test_recursive_multispan_pipeline.py")
text = path.read_text(encoding="utf-8")

old = '''    cfg["fiber"]["max_spans"] = 2
    validate_config(cfg)
'''

new = '''    cfg["fiber"]["max_spans"] = 2
    cfg["optimization"]["target_spans"] = 2
    cfg["optimization"]["evaluation_spans"] = [1, 2]
    validate_config(cfg)
'''

if old not in text:
    raise SystemExit("Could not find target block in test file.")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("Fixed recursive pipeline test config.")
