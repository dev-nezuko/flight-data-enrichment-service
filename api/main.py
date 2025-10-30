import os
import sys
from pathlib import Path
from uuid import uuid4

import django
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# The Django project lives in backend/; the flights app must be importable from here.
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from api.utils import make_aware  # noqa: E402
from api.validation_models import FlightData  # noqa: E402
from flights.models import EnrichmentTask, Flight  # noqa: E402
from flights.tasks import enrich_flight_task  # noqa: E402

app = FastAPI(title="Flight data enrichment service")


@app.post("/enrich-flight")
def enrich_flight(flight_data: FlightData):
    flight, _ = Flight.objects.update_or_create(
        flight_id=flight_data.id,
        defaults={
            "travel_class": flight_data.travel_class,
            "origin": flight_data.origin,
            "destination": flight_data.destination,
            "departure_time": make_aware(flight_data.departure_time),
            "arrival_time": make_aware(flight_data.arrival_time),
            "flight_numbers": flight_data.flight_numbers,
            "legs": [leg.model_dump(mode="json") for leg in flight_data.legs],
            "last_seen": make_aware(flight_data.last_seen),
            "enriched": False,
            "retail_price": None,
        },
    )

    task_id = str(uuid4())
    task = EnrichmentTask.objects.create(task_id=task_id, flight=flight, status="PENDING")

    try:
        enrich_flight_task.apply_async(args=[flight.flight_id], task_id=task_id)
    except Exception:
        # Broker errors can embed connection URLs, so only a generic message is stored.
        task.status = "FAILURE"
        task.result = {"error": "Unable to enqueue enrichment"}
        task.save(update_fields=["status", "result"])
        raise HTTPException(status_code=503, detail="Unable to enqueue enrichment") from None

    return {"task_id": task_id, "status": "PENDING"}


@app.get("/task-status/{task_id}")
def get_task_status(task_id: str):
    task = EnrichmentTask.objects.filter(task_id=task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task.task_id, "status": task.status, "result": task.result}
