from pathlib import Path

path = Path("releases/pnc-v1.0/reproduce_recursive_diagnostics.py")
text = path.read_text(encoding="utf-8-sig")

if "generate_joc_paper_evidence.py" in text:
    print("JOC evidence generator is already in the reproduction suite.")
    raise SystemExit(0)

lines = text.splitlines()
insert_at = None
inside_guard = False

for idx, line in enumerate(lines):
    if '"name": "scl_external_validation_claim_guard"' in line:
        inside_guard = True

    if inside_guard and line.strip() == "},":
        insert_at = idx + 1
        break

if insert_at is None:
    raise SystemExit("Could not find scl_external_validation_claim_guard block.")

block = [
    "    {",
    '        "name": "joc_paper_evidence_generation",',
    '        "command": [sys.executable, "scripts/generate_joc_paper_evidence.py"],',
    '        "expected_outputs": [',
    '            "releases/pnc-v1.0/generated/joc_paper_evidence_summary.json",',
    '            "releases/pnc-v1.0/generated/joc_figures/fig1_recursive_vs_analytical.pdf",',
    '            "releases/pnc-v1.0/generated/joc_figures/fig2_gnpy_vs_recursive_cband.pdf",',
    '            "releases/pnc-v1.0/generated/joc_figures/fig3_validation_rmse_summary.pdf",',
    '            "releases/pnc-v1.0/generated/joc_figures/fig4_grouped_cv_rmse.pdf",',
    '            "releases/pnc-v1.0/generated/joc_figures/fig5_cband_launch_power_sweep.pdf",',
    '            "releases/pnc-v1.0/generated/joc_figures/fig6_validation_readiness_by_band.pdf",',
    '            "releases/pnc-v1.0/generated/joc_tables/table1_validation_summary.csv",',
    '            "releases/pnc-v1.0/generated/joc_tables/table2_launch_power_sweep_summary.csv",',
    '            "releases/pnc-v1.0/generated/joc_tables/table3_validation_readiness.csv",',
    "        ],",
    "    },",
]

lines[insert_at:insert_at] = block

path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("Added JOC paper evidence generation to reproduction suite.")