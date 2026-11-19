"""Render prototype/kaggle/benchmarks.csv (one row per measured run) into the table in docs/models/README.md.

    python prototype/tools/build_benchmarks.py

Add a row to the CSV after every run instead of typing numbers into the docs; factsheets and status.md link here.
"""
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV = os.path.join(ROOT, "prototype", "kaggle", "benchmarks.csv")
MD = os.path.join(ROOT, "docs", "models", "README.md")
START, END = "<!-- BENCHMARKS:START -->", "<!-- BENCHMARKS:END -->"


def main():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    cols = ["model", "task", "scene", "hardware", "settings", "seconds", "peak_gb", "layers", "recomposite_diff", "note"]
    head = ["Model", "Task", "Scene", "Hardware", "Settings", "Time (s)", "Peak GB", "Layers", "Recomp. diff", "Note"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        cells = []
        for c in cols:
            v = (r.get(c) or "").strip()
            cells.append(v)
        lines.append("| " + " | ".join(cells) + " |")
    table = "\n".join(lines)
    note = (f"\n\nSource: `prototype/kaggle/benchmarks.csv` ({len(rows)} runs). Times exclude model loading. "
            "Recomposite diff: see [../glossary.md](../glossary.md).\n")
    s = open(MD, encoding="utf-8").read()
    a, b = s.index(START) + len(START), s.index(END)
    open(MD, "w", encoding="utf-8").write(s[:a] + "\n" + table + note + s[b:])
    print("table with", len(rows), "rows written to", MD)


if __name__ == "__main__":
    main()
