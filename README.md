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
- [Architecture Decisions](#architecture-decisions)
- [Feature Implementation Details](#feature-implementation-details)
- [Known Limitations and Future Improvements](#known-limitations-and-future-improvements)
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
flight-task-system/
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

## Architecture Decisions

### FastAPI + Django Combination
- **Rationale**: We chose to combine FastAPI with Django to leverage the best of both frameworks:
  - FastAPI provides high-performance async API capabilities and automatic OpenAPI documentation
  - Django offers a mature ORM, robust admin interface, and battle-tested security features
- **Trade-offs**:
  - Increased complexity in project setup
  - Better separation of concerns between API and data layers
  - Future-proof architecture that can scale independently

### Asynchronous Processing
- **Why Celery**:
  - Handles long-running flight data enrichment tasks without blocking API responses
  - Provides reliable task queuing with retry mechanisms
  - Supports task prioritization and scheduling
- **Redis as Message Broker**:
  - Low latency and high throughput
  - Built-in persistence
  - Excellent integration with Celery

### Data Storage Strategy
- **Current Implementation**:
  - Uses SQLite for development simplicity
  - Models designed for easy migration to PostgreSQL
  - Structured for efficient querying of flight data
- **Caching Layer**:
  - Redis used for caching frequent queries
  - Reduces load on the database
  - Improves response times for repeated requests

## Feature Implementation Details

### Flight Data Enrichment
1. **Data Reception**:
   - Validates incoming flight data against JSON schema
   - Normalizes dates and times to UTC
   - Performs initial data quality checks

2. **Task Processing**:
   ```python
   # Simplified flow
   @celery_app.task(retry_policy={
       'max_retries': 3,
       'interval_start': 0,
       'interval_step': 60,
       'interval_max': 180,
   })
   def enrich_flight_data(flight_id):
       # Fetch flight details
       # Query SerpAPI
       # Process and store results
   ```

3. **Price Enrichment Logic**:
   - Queries Google Flights via SerpAPI
   - Implements smart retry mechanism for rate limits
   - Handles currency conversions and normalization

### API Design
1. **Endpoint Structure**:
   - RESTful design principles
   - Versioned endpoints for future compatibility
   - Comprehensive error handling

2. **Authentication & Security**:
   - Token-based authentication
   - Rate limiting per client
   - Input validation and sanitization

### Monitoring and Logging
- Structured logging format
- Performance metrics collection
- Task queue monitoring

## Known Limitations and Future Improvements

### Current Limitations
1. **SerpAPI Dependencies**:
   - Rate limits on free tier
   - Occasional inconsistency in price data
   - Limited historical data access

2. **Scalability Constraints**:
   - Single Redis instance bottleneck
   - SQLite limitations in concurrent writes
   - Basic task prioritization

3. **Feature Gaps**:
   - Limited support for multi-currency
   - Basic error recovery mechanisms
   - Minimal analytics capabilities

### Planned Improvements

1. **Short-term (1-3 months)**:
   - [ ] Migrate to PostgreSQL for production
   - [ ] Implement Redis cluster for better scalability
   - [ ] Add comprehensive monitoring dashboard
   - [ ] Improve error handling and recovery
   - [ ] Add support for multiple flight search providers

2. **Medium-term (3-6 months)**:
   - [ ] Implement advanced caching strategies
   - [ ] Add real-time price update webhooks
   - [ ] Develop analytics dashboard
   - [ ] Add support for fare rules and conditions
   - [ ] Implement A/B testing framework

3. **Long-term (6+ months)**:
   - [ ] Machine learning for price prediction
   - [ ] Geographic distribution of services
   - [ ] Advanced analytics and reporting
   - [ ] Integration with additional data sources
   - [ ] Custom pricing algorithms

### Performance Optimization Plans
1. **Database Optimization**:
   - Implement database partitioning
   - Optimize indexes for common queries
   - Add materialized views for reports

2. **Caching Improvements**:
   - Implement multi-level caching
   - Add cache warming mechanisms
   - Optimize cache invalidation strategies

3. **API Enhancements**:
   - GraphQL support for flexible queries
   - Streaming responses for large datasets
   - Batch processing capabilities

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
