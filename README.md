# Flight Data Enrichment Service

This service enriches flight data with retail price information using the Google Flights API via SerpAPI.

## Table of Contents
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Development Setup](#development-setup)
- [Configuration](#configuration)
- [Running the Services](#running-the-services)
- [API Endpoints](#api-endpoints)
- [Testing](#testing)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)

## Features

- Asynchronous flight data enrichment
- REST API endpoints for submitting flights and checking task status
- Persistent storage of flight data and enrichment results
- Task queue system for handling enrichment requests
- Scalable architecture using FastAPI and Celery

## Prerequisites

Before setting up the project, ensure you have the following installed:
- Python 3.8 or higher
- Redis (for Celery message broker)
- Git
- A SerpAPI account and API key (for Google Flights data)

## Project Structure

```
flyflat_test/
├── api/                # FastAPI application
│   ├── main.py        # Main API entry point
│   └── routes/        # API route handlers
├── backend/           # Django backend
│   ├── models/        # Database models
│   └── tasks/         # Celery tasks
├── tests/             # Test suite
├── requirements.txt   # Python dependencies
└── .env.example      # Example environment variables
```

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/dev-nezuko/flight-data-enrichment-service.git
cd flight-data-enrichment-service
```

2. Create and activate a virtual environment:
```bash
python -m venv fly
source fly/bin/activate  # On Unix/macOS
# OR
.\fly\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a .env file from the example:
```bash
cp .env.example .env
```

5. Configure your environment variables in the .env file:
```
SERPAPI_KEY=your_api_key_here
DJANGO_SECRET_KEY=your_django_secret_key
DEBUG=True
REDIS_URL=redis://localhost:6379/0
```

6. Initialize the database:
```bash
python manage.py makemigrations
python manage.py migrate
```

## Configuration

### SerpAPI Setup
1. Sign up for a SerpAPI account at https://serpapi.com
2. Get your API key from the dashboard
3. Add the API key to your .env file

### Redis Setup
- **macOS** (using Homebrew):
  ```bash
  brew install redis
  brew services start redis
  ```
- **Linux**:
  ```bash
  sudo apt-get install redis-server
  sudo systemctl start redis-server
  ```
- **Windows**: Download and install from https://redis.io/download

## Running the Services

1. Start Redis (if not running as a service):
```bash
redis-server
```

2. Start the Celery worker:
```bash
celery -A backend worker --loglevel=info
```

3. Start the API server:
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

## API Endpoints

### POST /enrich-flight

Submit a flight for enrichment.

Request body:
```json
{
    "id": "string",
    "travel_class": "string",
    "origin": "string",
    "destination": "string",
    "departure_time": "datetime",
    "arrival_time": "datetime",
    "flight_numbers": ["string"],
    "legs": [{
        "origin": "string",
        "destination": "string",
        "departure_time": "datetime",
        "arrival_time": "datetime",
        "flight_number": "string",
        "aircraft_type": "string",
        "cabin_type": "string",
        "duration": "integer",
        "layover_time": "float",
        "distance": "integer"
    }],
    "last_seen": "datetime"
}
```

Response:
```json
{
    "task_id": "string",
    "status": "PENDING"
}
```

### GET /task-status/{task_id}

Check the status of an enrichment task.

Response:
```json
{
    "task_id": "string",
    "status": "string",
    "result": {
        "retail_price": "number"
    }
}
```

## Testing

1. Ensure the test database is configured:
```bash
python manage.py migrate --settings=backend.settings.test
```

2. Run the test suite:
```bash
pytest
```

3. For coverage report:
```bash
pytest --cov=.
```

## Architecture

The service uses a modern, scalable architecture:
- **FastAPI**: High-performance REST API framework
- **Django**: Robust ORM and data models
- **Celery**: Distributed task queue for async processing
- **Redis**: Message broker and caching
- **SQLite**: Development database (can be replaced with PostgreSQL for production)

## Troubleshooting

Common issues and solutions:

1. **Redis Connection Error**:
   - Verify Redis is running: `redis-cli ping`
   - Check Redis connection string in .env
   - Ensure Redis port (6379) is not blocked

2. **Celery Worker Issues**:
   - Verify Celery worker is running
   - Check logs for specific errors
   - Ensure Redis connection is stable

3. **Database Migration Issues**:
   - Delete the migrations folder and db.sqlite3
   - Run makemigrations and migrate again
   - Check Django settings for database configuration

For additional help, please create an issue on the GitHub repository. 