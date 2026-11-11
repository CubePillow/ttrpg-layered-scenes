"""Report broken relative links in all tracked (and new) Markdown files. Run before every push.

    python prototype/tools/check_doc_links.py            # list broken links, exit 1 if any
    python prototype/tools/check_doc_links.py --skip-archive
"""
import os
import re
import subprocess
import sys
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LINK = re.compile(r"\]\(([^)\s]+)\)")


def md_files():
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"], cwd=ROOT,
                         capture_output=True, text=True).stdout.split("\n")
    return sorted({f for f in out if f and os.path.exists(os.path.join(ROOT, f))})


def main():
    skip_archive = "--skip-archive" in sys.argv
    bad = 0
    for rel in md_files():
        if skip_archive and "/archive/" in rel.replace("\\", "/"):
            continue
        text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        for m in LINK.finditer(text):
            t = m.group(1)
            if re.match(r"^[a-z]+:", t) or t.startswith("#"):
                continue
            path = unquote(t.split("#", 1)[0])
            if not path:
                continue
            full = os.path.normpath(os.path.join(ROOT, os.path.dirname(rel), path))
            if not os.path.exists(full):
                print(f"{rel}: {t}"); bad += 1
    print(f"{bad} broken link(s)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
