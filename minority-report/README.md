# Minority Report
## Project Summary
- Status: Prototype
- Problem: Compare answers across multiple LLMs for the same questions
- Why AI: Detect outliers and consensus among model responses
- Artifacts: `minority-report.py`, `templates/`

This is a Flask app that takes a company name and a set of questions, queries multiple models (ChatGPT, Claude, Gemini placeholder), and renders a comparison table.

## Notes
- API keys are placeholders; you will need to wire real credentials.
- The Gemini integration is a stub.

## How to run
1. Install dependencies: `pip install -r requirements.txt` (if you add one)
2. Set environment variables for API keys.
3. Run: `python minority-report.py`
