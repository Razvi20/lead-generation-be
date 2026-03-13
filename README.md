# B2B Lead Generation Backend

A FastAPI backend that automates B2B lead generation by combining Google Places API, web scraping with Scrapy + Playwright, and AI-powered email personalization via OpenAI GPT-4o.

## Architecture

```
React Frontend
     │
     ├── GET  /api/autocomplete?q=...     → Location suggestions with viewport bounds
     ├── POST /api/generate-leads          → Returns job_id (async pipeline)
     └── GET  /api/jobs/{job_id}           → Poll for status + results
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
  Google Places   Scrapy     OpenAI
  (searchText)  (Playwright)  (GPT-4o)
        │           │           │
        └───────────┼───────────┘
                    ▼
              PostgreSQL
```

## Setup

### 1. Prerequisites

- Python 3.11+
- PostgreSQL running locally
- Node.js (for Playwright browsers)

### 2. Install dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install Playwright browsers (required for Scrapy-Playwright)
playwright install chromium
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your actual API keys and database URL
```

### 4. Set up the database

```bash
# Create the database
createdb leadgen

# Run migrations (or let FastAPI auto-create tables on startup)
alembic upgrade head
```

### 5. Generate initial migration (first time only)

```bash
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
```

### 6. Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

### `GET /api/autocomplete?q=Berlin`

Returns location suggestions with viewport bounds for the frontend map.

**Response:**

```json
{
  "predictions": [
    {
      "description": "Berlin, Germany",
      "place_id": "ChIJAVkDPzdOqEcRcD...",
      "viewport": {
        "low": { "latitude": 52.338, "longitude": 13.088 },
        "high": { "latitude": 52.675, "longitude": 13.761 }
      }
    }
  ]
}
```

### `POST /api/generate-leads`

Starts the async lead generation pipeline. Returns immediately with a job ID.

**Request:**

```json
{
  "sector": "plumbers",
  "bounds": {
    "low": { "latitude": 52.33, "longitude": 13.08 },
    "high": { "latitude": 52.67, "longitude": 13.76 }
  },
  "portfolio_url": "www.myagency.com"
}
```

**Response:**

```json
{ "job_id": "a1b2c3d4-..." }
```

### `GET /api/jobs/{job_id}`

Poll for job progress and results.

**Response (completed):**

```json
{
  "job_id": "a1b2c3d4-...",
  "status": "completed",
  "leads": [
    {
      "business_name": "Berlin Plumbing GmbH",
      "website": "https://berlin-plumbing.de",
      "email_found": "info@berlin-plumbing.de",
      "reviews": 3,
      "ai_email_draft": "Subject: Upgrade Your Online Presence..."
    }
  ],
  "error_message": null
}
```

## Environment Variables

| Variable          | Description                                               |
| ----------------- | --------------------------------------------------------- |
| `GOOGLE_API_KEY`  | Google Cloud API key (Places API enabled)                 |
| `OPENAI_API_KEY`  | OpenAI API key                                            |
| `DATABASE_URL`    | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins                              |

## Project Structure

```
├── app/
│   ├── main.py              # FastAPI app, CORS, lifespan
│   ├── config.py            # Environment settings
│   ├── database.py          # Async SQLAlchemy engine
│   ├── models.py            # Job + Lead ORM models
│   ├── schemas.py           # Pydantic request/response models
│   ├── routers/
│   │   ├── autocomplete.py  # GET /api/autocomplete
│   │   └── leads.py         # POST /api/generate-leads + GET /api/jobs/{id}
│   └── services/
│       ├── google_places.py # Google Places API client
│       ├── scraper.py       # Scrapy subprocess runner
│       ├── ai_personalizer.py # OpenAI email drafter
│       └── lead_pipeline.py # Pipeline orchestrator
├── scraper/
│   ├── scrapy.cfg
│   └── leadspider/
│       ├── settings.py      # Scrapy + Playwright config
│       ├── items.py
│       └── spiders/
│           └── website_spider.py  # Email extraction spider
├── alembic/                 # Database migrations
├── requirements.txt
└── .env.example
```
