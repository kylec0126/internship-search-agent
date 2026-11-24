"""Converts each application .docx to PDF with LibreOffice, then verifies:
one page each, Times New Roman embedded, and lists resume words not in the original.
Renders every page to _tools/previews/ for a visual check.

Lives in applications/_tools/ next to the build scripts (they hold resume content, so they're not published).
Usage: ORIGINAL_RESUME=path/to/resume.pdf python check_pdfs.py   (exit code 1 if any page/font check fails)
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pdfplumber

try:  # optional, gitignored: facts the student confirmed after the original resume was written
    from added_facts import GPA, TEXT as ADDED_TEXT
except ImportError:
    GPA, ADDED_TEXT = None, ""

HERE = Path(__file__).parent
APPS = HERE.parent
ORIGINAL = Path(os.environ.get("ORIGINAL_RESUME", HERE.parent / "base" / "original_resume.pdf"))  # never edited
PROFILE = HERE / ".lo_profile"
PREVIEWS = HERE / "previews"
TNR = sorted(Path("/System/Library/Fonts/Supplemental").glob("Times New Roman*.ttf"))


def soffice():
    for p in (shutil.which("soffice"), Path.home() / "Applications/LibreOffice.app/Contents/MacOS/soffice",
              Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")):
        if p and Path(p).exists():
            return str(p)
    sys.exit("LibreOffice not found (see apply.md for install steps)")


def font_profile():
    # Headless LibreOffice doesn't see macOS Supplemental fonts and swaps in Liberation Serif
    fonts = PROFILE / "user" / "fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    for f in TNR:
        link = fonts / f.name
        if not link.exists():
            link.symlink_to(f)
    return f"file://{PROFILE}"


def words(text):
    return set(re.findall(r"[a-z0-9$+.]+", text.lower().replace("’", "'")))


def main():
    exe, profile = soffice(), font_profile()
    # only the folders build_content.py rebuilt; submitted packages stay as they are
    content = json.loads((HERE / "content.json").read_text())
    dirs = [APPS / j["key"] for j in content["jobs"]] + ([APPS / "base"] if content.get("base") else [])
    for docx in sorted(f for d in dirs for f in d.glob("*.docx")):
        subprocess.run([exe, f"-env:UserInstallation={profile}", "--headless", "--convert-to", "pdf",
                        "--outdir", str(docx.parent), str(docx)], check=True, capture_output=True)

    global ORIGINAL_SHORT_LINES
    with pdfplumber.open(ORIGINAL) as pdf:
        original_text = pdf.pages[0].extract_text()
    original = words(original_text) | words(ADDED_TEXT)  # confirmed added facts count as original
    ORIGINAL_SHORT_LINES = {l.strip() for l in original_text.splitlines() if len(l.split()) <= 3}
    if GPA:
        ORIGINAL_SHORT_LINES.add(f"GPA: {GPA}/4.00")  # the original's GPA line, if the student updated it

    PREVIEWS.mkdir(exist_ok=True)
    ok = True
    for f in sorted(f for d in dirs for f in d.glob("*.pdf")):
        with pdfplumber.open(f) as pdf:
            fonts = {c["fontname"].split("+")[-1] for p in pdf.pages for c in p.chars}
            tnr = all(n.startswith("TimesNewRoman") for n in fonts)
            ok &= len(pdf.pages) == 1 and tnr
            print(f"{f.relative_to(APPS)}: pages={len(pdf.pages)} {'Times New Roman' if tnr else 'FONTS ' + str(sorted(fonts))}")
            if "Resume" in f.name:
                text = pdf.pages[0].extract_text()
                new = sorted(w.strip(".") for w in words(text) - original if w.strip("."))
                print(f"    words not in original resume: {new}")
                # wrapped lines of 1-3 words (e.g. "Power BI" or a lone "BI") look sloppy; the original's short lines
                # (headings, titles) are fine. Don't exempt all-caps lines: a wrapped "BI" is all caps too.
                orphans = [l for l in text.splitlines() if 0 < len(l.split()) <= 3
                           and l.strip() not in ORIGINAL_SHORT_LINES]
                if orphans:
                    ok = False
                    print(f"    ORPHAN LINES: {orphans}")
            for i, page in enumerate(pdf.pages, 1):
                page.to_image(resolution=110).save(PREVIEWS / f"{f.stem}_p{i}.png")
    print(f"previews: {PREVIEWS}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
