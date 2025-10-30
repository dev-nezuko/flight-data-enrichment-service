"""HTTP-level checks of the FastAPI routes; the Celery enqueue is patched out."""

from unittest.mock import patch

from django.test import TransactionTestCase
from fastapi.testclient import TestClient

from api.main import app
from flights.models import EnrichmentTask, Flight


def payload(**overrides):
    body = {
        "id": "synthetic-http-flight",
        "travel_class": "Economy",
        "origin": "JFK",
        "destination": "LAX",
        "departure_time": "2027-01-02T10:00:00Z",
        "arrival_time": "2027-01-02T16:00:00Z",
        "flight_numbers": ["DEMO1"],
        "legs": [
            {
                "origin": "JFK",
                "destination": "LAX",
                "departure_time": "2027-01-02T10:00:00Z",
                "arrival_time": "2027-01-02T16:00:00Z",
                "flight_number": "DEMO1",
                "aircraft_type": "Demo jet",
                "cabin_type": "Economy",
                "duration": 360,
                "layover_time": 0,
                "distance": 2475,
            }
        ],
        "last_seen": "2027-01-01T00:00:00Z",
    }
    body.update(overrides)
    return body


# TestClient runs sync routes on a worker thread, so rows must be committed to be visible.
class EnrichFlightRouteTests(TransactionTestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_submit_then_read_status(self):
        with patch("api.main.enrich_flight_task.apply_async") as enqueue:
            response = self.client.post("/enrich-flight", json=payload())
        self.assertEqual(response.status_code, 200)
        task_id = response.json()["task_id"]
        self.assertEqual(enqueue.call_args.kwargs["task_id"], task_id)

        flight = Flight.objects.get(flight_id="synthetic-http-flight")
        self.assertEqual(flight.legs[0]["departure_time"], "2027-01-02T10:00:00Z")

        status = self.client.get(f"/task-status/{task_id}")
        self.assertEqual(status.json(), {"task_id": task_id, "status": "PENDING", "result": None})

    def test_resubmission_resets_price_and_adds_a_task(self):
        with patch("api.main.enrich_flight_task.apply_async"):
            self.client.post("/enrich-flight", json=payload())
            Flight.objects.update(retail_price=99, enriched=True)
            self.client.post("/enrich-flight", json=payload())
        flight = Flight.objects.get()
        self.assertIsNone(flight.retail_price)
        self.assertFalse(flight.enriched)
        self.assertEqual(EnrichmentTask.objects.count(), 2)

    def test_unknown_task_is_404(self):
        self.assertEqual(self.client.get("/task-status/nope").status_code, 404)

    def test_broker_failure_is_503(self):
        with patch("api.main.enrich_flight_task.apply_async", side_effect=OSError("redis down")):
            response = self.client.post("/enrich-flight", json=payload())
        self.assertEqual(response.status_code, 503)
        self.assertEqual(EnrichmentTask.objects.get().status, "FAILURE")

    def test_rejects_invalid_input_without_writing(self):
        bad_bodies = [
            payload(origin="New York"),
            payload(origin="羽田"),
            payload(destination="lax"),
            payload(arrival_time="2027-01-02T09:00:00Z"),
            payload(id="x" * 101),
            payload(legs=[{**payload()["legs"][0], "distance": -1}]),
        ]
        for body in bad_bodies:
            with self.subTest(body=body), patch("api.main.enrich_flight_task.apply_async") as enq:
                self.assertEqual(self.client.post("/enrich-flight", json=body).status_code, 422)
                enq.assert_not_called()
        self.assertFalse(Flight.objects.exists())

    def test_naive_and_offset_times_compare_in_utc(self):
        body = payload(
            departure_time="2027-01-02T10:00:00", arrival_time="2027-01-02T12:00:00+01:00"
        )
        with patch("api.main.enrich_flight_task.apply_async"):
            self.assertEqual(self.client.post("/enrich-flight", json=body).status_code, 200)
