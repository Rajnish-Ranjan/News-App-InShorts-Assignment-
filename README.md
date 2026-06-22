# News App Backend API

## Features

- **Smart Search**: Parses natural language queries via Gemini and builds SQL filters automatically.
- **Geospatial Queries**: Fetch news articles based on user coordinates (`latitude`, `longitude`) using PostGIS.
- **Text Search**: PostgreSQL's `websearch_to_tsquery`.
- **Cursor-based Pagination**: All endpoints support cursor-based pagination.
- **LLM Summary Injection**: Asynchronously injects AI-generated summaries in each article.

---

## Project Structure

```text
├── app.py                      # FastAPI entry point and route definitions
├── models/                     # Data models
│   ├── request_params.py       # Pydantic models for API validation
│   ├── user.py
│   └── user_query.py
├── repositories/               # Pure Persistence Logic
│   ├── db.py                   # PostgreSQL connection pool manager
│   └── dbquery_builder.py      # Builds SQL from parsed intents
├── services/                   # Core business logic
│   ├── query_service.py
│   └── trending_service.py
├── utils/                      # Helper utilities
│   ├── cursor_utils.py
│   └── llm.py
└── tests/                      # Sample JSON data and testing scripts
```

---

## Setup & Installation

### 1. Requirements
- Python 3.12
- PostgreSQL DB
- API Key for LLM provider (e.g., Gemini )

### 2. Environment Variables
(`.env` file):
```env
DB_HOST = your-db-host
DB_PORT = 5432
DB_USER = your-db-user
DB_PASSWORD = your-db-password
DB_NAME = your-db-name
DB_SSLMODE = require

# Add your LLM keys here
GEMINI_API_KEY = your-gemini-key
```

### 3. Running the Server
```bash
pip install -r requirements.txt
python app.py # port 8000
```
*(use `uvicorn app:app --reload` for hot-reloading).*

---

## Core API Endpoints

All endpoints support cursor-based pagination via the `limit` and `cursor` parameters.

### `GET /news/api/v1/smart-search`
Construct a highly specific SQL query.
- **Params**: `query="latest tech news in Bangalore"`
- **Headers**: `x-user-lat`, `x-user-lon`

### `GET /news/api/v1/category`
Predefined category.
- **Params**: `category="technology"`

### `GET /news/api/v1/nearby`
Fetch based upon radius of the user's location.
- **Params**: `radius=50` (in km)
- **Headers**: `x-user-lat`, `x-user-lon` (Required)

### `GET /news/api/v1/search`
Perform a text search on article contents
- **Params**: `query="artificial intelligence"`

### `GET /news/api/v1/trending`
Fetch currently trending news