"""
Resume → Word Cloud (v3, Claude Code approach)

Uses the `claude` CLI for skill extraction — no API key or credits needed,
runs via your existing Claude Code subscription.

Pipeline: pdfminer (text extract) → claude -p (skill weights as JSON) → WordCloud
"""

import json
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from wordcloud import WordCloud
from io import StringIO

HERE = Path(__file__).parent

PROMPT = """Analyze this resume and return a JSON object mapping skill/theme strings to an integer weight (1-10) reflecting how central each is to this person's professional identity.

Rules:
- 30-50 terms total
- Prefer concrete skills, tools, domains, and signature achievements over generic words
- Include multi-word phrases where more meaningful (e.g. "Machine Learning" not just "Learning")
- Capture the person's distinctive story, not just a generic data resume
- No punctuation in keys, title case

Return ONLY valid JSON, no prose, no markdown fences.
Example: {"Python": 8, "Machine Learning": 9, "Data Strategy": 7}

Resume:
"""


# -- 1. Extract PDF text -----------------------------------------------------

def extract_pdf_text(pdf_path: Path) -> str:
    output = StringIO()
    manager = PDFResourceManager()
    converter = TextConverter(manager, output, laparams=LAParams())
    interpreter = PDFPageInterpreter(manager, converter)
    with open(pdf_path, "rb") as f:
        for page in PDFPage.get_pages(f, set()):
            interpreter.process_page(page)
    converter.close()
    text = output.getvalue()
    output.close()
    return text


# -- 2. Extract skills via claude CLI ----------------------------------------

def extract_skills_with_weights(resume_text: str) -> dict[str, int]:
    result = subprocess.run(
        ["claude", "-p", PROMPT + resume_text],
        capture_output=True,
        text=True,
        check=True,
    )
    raw = result.stdout.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
        raw = raw.rsplit("```", 1)[0].strip()
    return json.loads(raw)


# -- 3. Generate word cloud --------------------------------------------------

def generate_wordcloud(weights: dict[str, int], output_path: Path, mask_path: Path | None = None):
    if mask_path and mask_path.exists():
        mask = np.array(Image.open(mask_path))
        wc = WordCloud(
            background_color="white",
            max_words=200,
            mask=mask,
            contour_width=3,
            contour_color="white",
            prefer_horizontal=0.85,
            colormap="Blues",
        ).generate_from_frequencies(weights)
        figsize = (20, 10)
    else:
        wc = WordCloud(
            background_color="white",
            max_words=200,
            width=1600,
            height=800,
            prefer_horizontal=0.85,
            colormap="Blues",
        ).generate_from_frequencies(weights)
        figsize = (16, 8)

    plt.figure(figsize=figsize)
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {output_path}")
    wc.to_file(HERE / "linkedin_wordcloud_header.png")
    print(f"Saved: {HERE / 'linkedin_wordcloud_header.png'}")


# -- main --------------------------------------------------------------------

if __name__ == "__main__":
    resume_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "resume.pdf"

    print("Extracting text from PDF...")
    text = extract_pdf_text(resume_path)

    print("Asking Claude to extract and weight skills...")
    weights = extract_skills_with_weights(text)

    print(f"\nClaude identified {len(weights)} skills:")
    for skill, weight in sorted(weights.items(), key=lambda x: -x[1]):
        print(f"  {weight:2d}  {skill}")

    print("\nGenerating word cloud...")
    generate_wordcloud(
        weights,
        output_path=HERE / "output_v3.png",
        mask_path=HERE / "linkedin_header_template.png",
    )

    print("\nDone. Open with:")
    print(f"  open {HERE / 'output_v3.png'}")
