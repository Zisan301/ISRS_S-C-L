from pathlib import Path

# Patch optimization objective
path = Path("src/isrs_scl/optimization/adaptive_isrs.py")
text = path.read_text(encoding="utf-8")

old = '        result = link.evaluate(dbm_to_w(profile), spans)\n'
new = '        evaluator = getattr(link, "evaluate_recursive", link.evaluate)\n        result = evaluator(dbm_to_w(profile), spans)\n'

if old not in text:
    raise SystemExit("Could not find optimizer evaluate() call.")
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("Patched optimizer to prefer evaluate_recursive().")


# Patch publication strategy sweeps
path = Path("src/isrs_scl/experiments.py")
text = path.read_text(encoding="utf-8")

old = '''    for strategy, profile in profiles.items():
        for result in link.sweep_spans(dbm_to_w(profile)):
            frame = result.to_frame(link.grid); frame.insert(0, "strategy", strategy); frame.insert(1, "spans", result.n_spans); channel_tables.append(frame)
'''

new = '''    for strategy, profile in profiles.items():
        evaluator = getattr(link, "evaluate_recursive", link.evaluate)
        launch_w = dbm_to_w(profile)
        for n_spans in range(1, int(cfg["fiber"]["max_spans"]) + 1):
            result = evaluator(launch_w, n_spans)
            frame = result.to_frame(link.grid); frame.insert(0, "strategy", strategy); frame.insert(1, "spans", result.n_spans); channel_tables.append(frame)
'''

if old not in text:
    raise SystemExit("Could not find _strategy_sweeps loop.")
text = text.replace(old, new, 1)

old = '    power = link.evaluate(dbm_to_w(profile_dbm), target_spans)\n'
new = '    evaluator = getattr(link, "evaluate_recursive", link.evaluate)\n    power = evaluator(dbm_to_w(profile_dbm), target_spans)\n'

if old not in text:
    raise SystemExit("Could not find waveform validation evaluate() call.")
text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("Patched experiments pipeline to prefer evaluate_recursive().")
