"""
Resume → Word Cloud (v1, 2024 approach)

Pipeline: pdfminer → NLTK tokenize/lemmatize → spaCy noun chunks → skills.csv dictionary match → WordCloud

Original: https://colab.research.google.com/drive/1Ss9e7Hqz85YArnJ1LNiDYF8YGCsSZQJX
Adapted to run locally (paths fixed, Colab magic removed).
"""

import re
import sys
from io import StringIO
from pathlib import Path

import en_core_web_sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nltk
import numpy as np
import pandas as pd
import spacy
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from PIL import Image
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from wordcloud import WordCloud

nltk.download("wordnet", quiet=True)
nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
nltk.download("stopwords", quiet=True)

HERE = Path(__file__).parent


# -- 1. Parse PDF ------------------------------------------------------------

def resume_parser(fname, pages=None):
    pagenums = set(pages) if pages else set()
    output = StringIO()
    manager = PDFResourceManager()
    converter = TextConverter(manager, output, laparams=LAParams())
    interpreter = PDFPageInterpreter(manager, converter)
    with open(fname, "rb") as infile:
        for page in PDFPage.get_pages(infile, pagenums):
            interpreter.process_page(page)
    converter.close()
    text = output.getvalue()
    output.close()
    return text


# -- 2. Extract skills -------------------------------------------------------

def extract_skills(resume_text):
    resume_text = re.sub(r"[-,()\\.!?]", "", resume_text).lower()

    lemmatizer = WordNetLemmatizer()
    tokens = nltk.word_tokenize(resume_text)
    tokens = [lemmatizer.lemmatize(t) for t in tokens]
    stop_words = stopwords.words("english")
    tokens = [t for t in tokens if t not in stop_words]

    skills_df = pd.read_csv(HERE / "skills.csv")
    skills = list(skills_df.columns.values)

    relevant_skills = []

    # unigrams
    for token in tokens:
        if token.lower() in skills:
            relevant_skills.append(token)

    # bi/tri-grams via spaCy noun chunks
    nlp = en_core_web_sm.load()
    nlp_text = nlp(resume_text)
    for chunk in nlp_text.noun_chunks:
        token = chunk.text.lower().strip()
        if token in skills:
            relevant_skills.append(token)

    return [i.capitalize() for i in set(i.lower() for i in relevant_skills)]


# -- 3. Generate word cloud --------------------------------------------------

def generate_wordcloud(skills, output_path, mask_path=None):
    skills_string = " ".join(skills)

    if mask_path and Path(mask_path).exists():
        mask = np.array(Image.open(mask_path))
        wc = WordCloud(
            background_color="white",
            max_words=1000,
            mask=mask,
            contour_width=3,
            contour_color="white",
        ).generate(skills_string)
        figsize = (20, 10)
    else:
        wc = WordCloud(
            max_font_size=50, max_words=100, background_color="white"
        ).generate(skills_string)
        figsize = (10, 6)

    plt.figure(figsize=figsize)
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {output_path}")
    plt.show()
    return wc


# -- main --------------------------------------------------------------------

if __name__ == "__main__":
    resume_path = sys.argv[1] if len(sys.argv) > 1 else HERE / "resume.pdf"

    print("Parsing PDF...")
    text = resume_parser(resume_path)

    print("Extracting skills via NLTK + spaCy + skills.csv dictionary...")
    skills = extract_skills(text)
    print(f"Found {len(skills)} skills: {skills}")

    print("Generating word cloud...")
    generate_wordcloud(
        skills,
        output_path=HERE / "output_v1.png",
        mask_path=HERE / "linkedin_header_template.png",
    )
