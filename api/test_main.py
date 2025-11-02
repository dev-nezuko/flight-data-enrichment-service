# Third-party imports
import pytest
from fastapi.testclient import TestClient

# Local application imports
from api.main import app

client = TestClient(app)

# Sample flight data matching your schema (use ISO datetimes)
sample_flight = {
    "id": "20250613-MS-MS986-MS747",
    "travel_class": "Business",
    "origin": "JFK",
    "destination": "ATH",
    "departure_time": "2025-06-13T12:55:00",
    "arrival_time": "2025-06-14T12:10:00",
    "flight_numbers": ["MS986", "MS747"],
    "legs": [
        {
            "origin": "JFK",
            "destination": "CAI",
            "departure_time": "2025-06-13T12:55:00",
            "arrival_time": "2025-06-14T06:15:00",
            "flight_number": "MS986",
            "aircraft_type": "Boeing 777",
            "cabin_type": "Business",
            "duration": 620,
            "layover_time": 235.0,
            "distance": 5614,
        },
        {
            "origin": "CAI",
            "destination": "ATH",
            "departure_time": "2025-06-14T10:10:00",
            "arrival_time": "2025-06-14T12:10:00",
            "flight_number": "MS747",
            "aircraft_type": "Boeing 737",
            "cabin_type": "Business",
            "duration": 120,
            "layover_time": 0.0,
            "distance": 688,
        },
    ],
    "last_seen": "2025-05-29T03:38:05Z"
}

def test_enrich_flight():
    response = client.post("/enrich-flight", json=sample_flight)
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "PENDING"

def test_task_status_not_found():
    response = client.get("/task-status/invalid-task-id")
    assert response.status_code == 404
