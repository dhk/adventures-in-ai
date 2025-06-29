# Architecture Diagram

## Version 1a

## Version 1: 2025-06-28 - conceptual, whole product solution


This came straight out of ChatGPT. 

```
ok. i need a mermaid document that describes the architecture to support the following. Bear in mind that I want to host it on github (for now) and use google cloud for image storage.

I"ll need to build a service that is an SMTP end point so that people can email pictures (or URLs of pictures) to me
```

```mermaid
flowchart TD
    subgraph User Interaction
        U1[User<br/>submits email with image or URL]
        U2[User<br/>uploads via Web UI]
    end

    subgraph GitHub-Hosted Service
        S1[SMTP Server Endpoint<br/>receives emails]
        S2[Image Scraper<br/>for URL extraction]
        S3[Validation Pipeline<br/>AI-based kitty detector]
        S4[Upload to GCS<br/>Google Cloud Storage]
        S5[Metadata Tracker<br/>PostgreSQL or GCS metadata]
        S6[Random Image Picker<br/>without replacement]
        S7[Instagram Poster<br/>via API or headless]
        S8[Scheduler<br/>GitHub Actions or GCP Scheduler]
        S9[Usage Logger<br/>GCS logs, Pub/Sub, or custom]
        S10[Admin Web UI<br/>moderation + metrics]
    end

    subgraph Google Cloud
        GCS[Google Cloud Storage<br/>kitty_images/]
        LOGS[Cloud Logging / Monitoring]
    end

    INSTAGRAM[(Instagram)]
    AdminYou[You]

    U1 --> S1 --> S2 --> S3 --> S4
    U2 --> S3
    S3 --> GCS
    GCS --> S5
    S5 --> S6 --> S7
    S8 --> S6
    S7 --> INSTAGRAM
    S4 --> LOGS
    S7 --> LOGS
    S9 --> LOGS
    LOGS --> S10
    S10 --> AdminYou

 ```



| Component               | Purpose                                      |
| ----------------------- | -------------------------------------------- |
| **SMTP Endpoint**       | Accepts emailed image attachments or URLs    |
| **Scraper / Extractor** | Gets image content from email or web links   |
| **Validation Pipeline** | Uses AI to detect if the image is a kitten   |
| **GCS**                 | Permanent storage for approved KIs           |
| **Random Picker**       | Pulls 3 new KIs, no repeats                  |
| **Instagram Poster**    | Uses API or headless script to post          |
| **Scheduler**           | Triggers 3KI posting job                     |
| **Admin UI**            | Moderate, track metrics, uploads             |
| **Logger**              | Tracks usage, errors, and engagement         |
| **GitHub**              | Hosts all code, CI/CD optionally via Actions |
