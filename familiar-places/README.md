# Familiar Places

Familiar Places compares neighborhoods using civic open-data signals. Raw point
records are loaded into DuckDB, aggregated into H3 cells, and matched with cosine
similarity over normalized feature vectors.

## Run locally

```bash
cd /Users/dhk/Documents/dev/adventures-in-ai/familiar-places
python -m pip install -r requirements.txt
/opt/anaconda3/bin/python3.11 -m streamlit run app.py
```

Use **Seed demo data** in the sidebar to create a local DuckDB database with
sample city data.

## Pipeline

- `pipeline/ingest.py`: fetches Socrata API records and writes normalized NDJSON.
- `pipeline/load.py`: initializes DuckDB and loads cached raw records.
- `pipeline/score.py`: aggregates raw records into H3 feature rows.
- `pipeline/similarity.py`: finds neighborhoods with similar feature profiles.

