# Job Application Agent — Write + auto-fill (steps 5–7)

Run tools from the repository root (your current directory).

1. **Rank** the jobs 0–100 using the skill map, then order them by the **Ranking rules for all job searches** in `market.md`: deadline within 10 days first, then posted in the last 14 days, then fit. Apply its 60-day cutoff, 3-application cap, title screen and 55+ display rule. Show the top 5 as a table: `Rank | Title | Company | Fit | Deadline | Days since posted | Why`.
2. **Write the application** for each chosen job:
   - Tailored cover letter (150–200 words, 3 paragraphs).
   - A full tailored resume (see "Application package" below), not just a list of bullet rewrites.
   - Reference REAL experience from the resume. Never fabricate. No "I am writing to express my interest."
3. **Save the application package** (below) for each job.
4. **Auto-fill demo** (mock form, reliable and reproducible):
   - Serve it: `python -m http.server` inside `demo/`, then open the localhost URL for `demo/application_form.html`.
   - Generate a résumé PDF for file-upload fields: `python tools/make_resume_pdf.py student_resume.txt my_job_data_center/<name>.pdf`. When a tailored resume PDF exists from step 3, upload that one instead.
   - Fill fields with Playwright via CSS id selectors (`#firstName`, `#email`, `#gradYear` combobox, `#authorized` checkbox, etc.). Upload the PDF via the file input.

## Application package

One folder per job: `applications/<company-slug>/` (e.g. `applications/stripe/`). `applications/` is gitignored because it holds the student's contact details. Never write to or overwrite the student's original resume file.

Files in each folder (`<First>_<Last>` from the resume, `<Company>` short and CamelCase, e.g. `GreyState`):

| File | Contents |
|---|---|
| `<First>_<Last>_Cover_Letter_<Company>.docx` + `.pdf` | Cover letter only: name/contact header, date, "Hiring Team / <Company>", "Dear Hiring Team,", the 3 paragraphs, "Sincerely, <Name>". No fit score, posting link, or bullets. |
| `<First>_<Last>_Resume_<Company>.docx` + `.pdf` | The complete resume, tailored to this job. Exactly ONE page. |
| `notes.md` | Posting link, fit score, tracker status, and the to-dos before applying (work authorization, official posting URL if the link is an aggregator, any skill gap worth closing first). |

### Tailored resume rules
- **Start from the original resume and keep everything:** every section in the same order, every entry, every date, education, GPA, interests. Same layout: match the original's page size, margins, font, font sizes, heading rules, and right-aligned locations/dates. Inspect the original PDF's fonts/sizes/margins first (e.g. PyMuPDF `get_text("dict")`) instead of guessing.
- **Tailoring means only:** reorder bullets within each entry so the most relevant come first; reword a bullet using the JD's vocabulary; reorder the skills line so the posting's tools come first. Section and entry order stay as in the original. The student may approve a specific exception (e.g. a different project leads PROJECTS for one role family); record it here with the date it was approved.
- **Facts added after the original resume:** if the student confirms a real skill or fact that isn't on the resume yet, record it in `applications/_tools/added_facts.py` (gitignored). Only those confirmed facts may be added; the word check treats them as part of the original.
- **Every claim must already be in the original resume.** A rewrite can change verbs and word order. It can't add a number, tool, outcome, scope, or adjective the original doesn't support (e.g. no "to protect data integrity", no "to speed up development"). A skill may move into the skills line only if a bullet in the original already shows it. Keep qualifiers (e.g. "Experience in Power BI" stays a qualified claim).
- Keep the original bullets verbatim unless a rewrite clearly improves the match.

### Building and verifying the files
- **If `applications/_tools/build.sh` exists, use it; don't rewrite the scripts.** For a new job, add an entry to `jobs` in `applications/_tools/build_content.py` (reusing its original-bullet text `O[...]`), write the letter to `applications/_tools/letters/<key>.txt`, then run `applications/_tools/build.sh`. It builds every .docx and PDF and runs checks 1, 2 and 4 below. You still do checks 3 and 5 yourself (images are in `applications/_tools/previews/`).
- Build the `.docx` files with docx-js (see the docx skill). Convert to PDF with LibreOffice: `soffice --headless --convert-to pdf`.
  - LibreOffice missing: `brew install --cask libreoffice`. If Homebrew fails, use the official DMG from download.documentfoundation.org: verify its published SHA-256, then copy `LibreOffice.app` to `~/Applications`.
  - Headless LibreOffice on macOS may not see `/System/Library/Fonts/Supplemental` (e.g. Times New Roman) and silently substitutes Liberation Serif. Fix: a dedicated profile (`-env:UserInstallation=file://<dir>`) whose `user/fonts/` symlinks the needed font files.
- **Verify before reporting done:**
  1. Every resume PDF is exactly 1 page, and every cover letter PDF is 1 page.
  2. The embedded fonts match the original resume's fonts.
  3. Render every page to an image and look at it. Check for clean alignment, no orphan line of 1–3 words, and spacing that matches the original.
  4. List every word in each tailored resume that doesn't appear in the original resume, and review each one. Inflections and rephrasings of existing claims are fine; anything that adds a fact gets reverted.
  5. Check time words against today's date and the resume's dates (e.g. "last summer" for a job two summers ago is wrong; say "In summer 2025").

**HARD RULES when filling any form (real or demo):**
- **NEVER click submit.** Fill every field, then stop at the submit button — the human decides.
- **NEVER fill honeypot** anti-bot fields (e.g. a hidden box labeled "leave this empty"). Filling one flags the applicant as a bot.
- **NEVER fabricate protected identity fields** (disability / veteran / race / gender). Leave blank or select "decline to self-identify". Objective facts (work authorization, location, field of study) may be filled honestly from the resume.
