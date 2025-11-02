# Standard library imports
import os
import sys
from datetime import datetime
from typing import List
from uuid import uuid4

# Third-party imports
import django
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(env_path)

# Ensure the Django project directory is in sys.path so Python can find flights
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

# print("sys.path after insertion:", sys.path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

import django
django.setup()

# Local application imports
from flights.models import Flight, EnrichmentTask
from flights.tasks import enrich_flight_task
from api.validation_models import FlightData
from api.utils import make_aware

app = FastAPI()



@app.post("/enrich-flight")
def enrich_flight(flight_data: FlightData):
    # Save or update Flight record in DB
    flight, _ = Flight.objects.update_or_create(
        flight_id=flight_data.id,
        defaults={
            "travel_class": flight_data.travel_class,
            "origin": flight_data.origin,
            "destination": flight_data.destination,
            "departure_time": make_aware(flight_data.departure_time),
            "arrival_time": flight_data.arrival_time,
            "flight_numbers": flight_data.flight_numbers,
            "legs": [
                {
                    **{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in leg.model_dump().items()}
                }
                for leg in flight_data.legs
                    ],
            "last_seen": flight_data.last_seen,
            "enriched": False,
            "retail_price": None,
        }
    )

    # Create a new EnrichmentTask record with a unique task_id
    task_id = str(uuid4())
    EnrichmentTask.objects.create(
        task_id=task_id,
        flight=flight,
        status='PENDING',
    )

    # Enqueue Celery task asynchronously with the task_id
    celery_result = enrich_flight_task.apply_async(args=[flight.flight_id], task_id=task_id)

    return {"task_id": celery_result.id, "status": "PENDING"}


@app.get("/task-status/{task_id}")
def get_task_status(task_id: str):
    try:
        task = EnrichmentTask.objects.get(task_id=task_id)
        return {
            "task_id": task.task_id,
            "status": task.status,
            "result": task.result,
        }
    except EnrichmentTask.DoesNotExist:
        raise HTTPException(status_code=404, detail="Task not found")

