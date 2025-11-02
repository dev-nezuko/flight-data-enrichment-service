# Flight Data Enrichment Service

This service enriches flight data with retail price information using the Google Flights API via SerpAPI.

## Features

- Asynchronous flight data enrichment
- REST API endpoints for submitting flights and checking task status
- Persistent storage of flight data and enrichment results
- Task queue system for handling enrichment requests

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
export SERPAPI_KEY=your_api_key_here
```

3. Initialize the database:
```bash
python manage.py migrate
```

4. Start the services:
```bash
# Start Redis (required for Celery)
redis-server

# Start Celery worker
celery -A backend worker --loglevel=info

# Start the API server
uvicorn api.main:app --reload
```

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

Run the test suite:
```bash
pytest
```

## Architecture

- FastAPI for the REST API
- Django for data models and ORM
- Celery for task queue
- Redis for message broker
- SQLite for data storage (can be replaced with PostgreSQL for production) 