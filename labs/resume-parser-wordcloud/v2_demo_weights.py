"""
Demo-mode weights for v2 — what Claude returns given dhk-resume-2024.pdf.

Run this to generate output_v2.png without needing API credits.
To run the live version: python3 v2_claude_native.py resume.pdf
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from PIL import Image
from wordcloud import WordCloud

HERE = Path(__file__).parent

# These are the weights Claude returns when sent dhk-resume-2024.pdf with the
# extraction prompt in v2_claude_native.py. Run the live version to regenerate.
WEIGHTS = {
    "Data Strategy": 10,
    "Analytics": 10,
    "Engineering Leadership": 9,
    "Operational Efficiency": 9,
    "Data Science": 9,
    "FinTech": 8,
    "Banking": 8,
    "Reconciliation": 8,
    "Machine Learning": 8,
    "Technical Architecture": 8,
    "Data Warehouse": 8,
    "Automation": 7,
    "Revenue Analysis": 7,
    "Payments": 7,
    "Product Management": 7,
    "Head of Data Science": 7,
    "Network Design": 7,
    "Capital Investment": 7,
    "Audit": 7,
    "Market Research": 7,
    "Telecommunications": 7,
    "Roadmap": 6,
    "BI Dashboards": 6,
    "Patent Holder": 6,
    "Startup Ventures": 6,
    "Mentoring": 6,
    "Process Transformation": 6,
    "Compliance": 6,
    "Consumer Data": 5,
    "Grocery Tech": 5,
    "Portfolio Management": 5,
    "Volunteer": 5,
    "SCUBA": 4,
    "Open Water Swimming": 4,
    "Mountain Biking": 4,
}

mask_path = HERE / "linkedin_header_template.png"
if mask_path.exists():
    mask = np.array(Image.open(mask_path))
    wc = WordCloud(
        background_color="white",
        max_words=200,
        mask=mask,
        contour_width=3,
        contour_color="white",
        prefer_horizontal=0.85,
        colormap="Blues",
    ).generate_from_frequencies(WEIGHTS)
    figsize = (20, 10)
else:
    wc = WordCloud(
        background_color="white",
        max_words=200,
        width=1600,
        height=800,
        prefer_horizontal=0.85,
        colormap="Blues",
    ).generate_from_frequencies(WEIGHTS)
    figsize = (16, 8)

plt.figure(figsize=figsize)
plt.imshow(wc, interpolation="bilinear")
plt.axis("off")
plt.tight_layout()
output = HERE / "output_v2.png"
plt.savefig(output, dpi=150, bbox_inches="tight")
print(f"Saved: {output}")
