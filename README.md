# Agentic Retail Demo

An agentic application demonstrating retail workflows using Google ADK, Gemini, and BigQuery.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables**:
    Copy `.env.example` to `.env` and fill in your values:
    ```bash
    cp .env.example .env
    ```

3.  **Run Locally**:
    ```bash
    uvicorn main:app --reload
    ```

## Deployment

Deploy to Cloud Run using the `deploy.sh` script (ensure you have `gcloud` installed and authenticated).

```bash
./deploy.sh
```
