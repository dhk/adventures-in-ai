"""
Resume → Word Cloud (v2, 2026 approach)

Pipeline: PDF → Claude API (direct document input) → structured skill weights → WordCloud

No NLP pipeline. No skills dictionary. No spaCy model downloads.
Claude reads the resume as a document, returns skills with importance weights,
and those weights drive word size directly.
"""

import base64
import json
import sys
from pathlib import Path

import anthropic
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from wordcloud import WordCloud

HERE = Path(__file__).parent

CLIENT = anthropic.Anthropic()


# -- 1. Extract skills via Claude --------------------------------------------

EXTRACTION_PROMPT = """
You are analyzing a resume to extract skills and themes for a LinkedIn header word cloud.

Return a JSON object mapping skill/theme strings to an integer weight (1–10) reflecting
how central each is to this person's professional identity. Higher weight = larger in the cloud.

Rules:
- 30–50 terms total
- Prefer concrete skills, tools, domains, and signature achievements over generic words
- Include multi-word phrases where they are more meaningful than individual words
  (e.g. "Machine Learning" not just "Learning")
- Capture the person's distinctive story, not just a generic data resume
- No punctuation in keys, title case

Return ONLY valid JSON, no prose. Example shape:
{"Python": 8, "Machine Learning": 9, "Data Strategy": 7}
"""


def extract_skills_with_weights(pdf_path: Path) -> dict[str, int]:
    pdf_bytes = pdf_path.read_bytes()
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    response = CLIENT.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {"type": "text", "text": EXTRACTION_PROMPT},
                ],
            }
        ],
    )

    raw = response.content[0].text.strip()
    # strip markdown code fences if present
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:-1])

    return json.loads(raw)


# -- 2. Generate word cloud from weighted skills -----------------------------

def generate_wordcloud(weights: dict[str, int], output_path: Path, mask_path: Path | None = None):
    # WordCloud accepts a frequency dict — use weight directly as frequency
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
    plt.show()


# -- main --------------------------------------------------------------------

if __name__ == "__main__":
    resume_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "resume.pdf"

    print("Sending PDF to Claude for skill extraction...")
    weights = extract_skills_with_weights(resume_path)

    print(f"Claude identified {len(weights)} skills:")
    for skill, weight in sorted(weights.items(), key=lambda x: -x[1]):
        print(f"  {weight:2d}  {skill}")

    print("\nGenerating word cloud...")
    generate_wordcloud(
        weights,
        output_path=HERE / "output_v2.png",
        mask_path=HERE / "linkedin_header_template.png",
    )
