"""Worker behaviour against a faked provider; no network or broker is used."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import httpx
from django.test import TestCase, override_settings

from flights.models import EnrichmentTask, Flight
from flights.tasks import EnrichmentError, enrich_flight_task

FAKE_URL = "http://provider.invalid/search.json"
SEARCH_FIXTURE = {"best_flights": [{"price": 412}, {"price": 530}]}


def provider_response(status=200, payload=None):
    request = httpx.Request("GET", FAKE_URL)
    return httpx.Response(status, json=payload if payload is not None else {}, request=request)


@override_settings(SERPAPI_KEY="placeholder-key", SERPAPI_URL=FAKE_URL)
class EnrichFlightTaskTests(TestCase):
    def setUp(self):
        departure = datetime(2027, 3, 4, 9, tzinfo=UTC)
        self.flight = Flight.objects.create(
            flight_id="fixture-flight",
            travel_class="Economy",
            origin="JFK",
            destination="LAX",
            departure_time=departure,
            arrival_time=departure,
            flight_numbers=["DEMO1"],
            legs=[],
            last_seen=departure,
        )
        self.task = EnrichmentTask.objects.create(task_id="fixture-task", flight=self.flight)

    def run_task(self, responses):
        client = Mock()
        client.get.side_effect = responses
        with patch("flights.tasks.httpx.Client") as client_cls:
            client_cls.return_value.__enter__.return_value = client
            result = enrich_flight_task.apply(args=["fixture-flight"], task_id="fixture-task")
        self.task.refresh_from_db()
        self.flight.refresh_from_db()
        return result, client

    def test_success_stores_first_best_price(self):
        result, client = self.run_task([provider_response(payload=SEARCH_FIXTURE)])
        self.assertEqual(result.result, {"retail_price": 412.0})
        self.assertEqual(self.task.status, "SUCCESS")
        self.assertEqual(self.flight.retail_price, Decimal("412.00"))
        self.assertTrue(self.flight.enriched)
        self.assertEqual(client.get.call_args.args[0], FAKE_URL)
        self.assertEqual(client.get.call_args.kwargs["params"]["outbound_date"], "2027-03-04")

    def test_no_price_is_success_but_not_enriched(self):
        self.run_task([provider_response(payload={"best_flights": []})])
        self.assertEqual(self.task.status, "SUCCESS")
        self.assertEqual(self.task.result["retail_price"], None)
        self.assertIn("detail", self.task.result)
        self.assertFalse(self.flight.enriched)

    def test_transient_errors_are_retried_then_succeed(self):
        result, client = self.run_task(
            [
                httpx.ConnectError("boom", request=httpx.Request("GET", FAKE_URL)),
                provider_response(503),
                provider_response(payload=SEARCH_FIXTURE),
            ]
        )
        self.assertEqual(client.get.call_count, 3)
        self.assertEqual(self.task.status, "SUCCESS")
        self.assertEqual(result.result["retail_price"], 412.0)

    def test_transient_errors_fail_after_max_retries(self):
        result, client = self.run_task([provider_response(503)] * 4)
        self.assertEqual(client.get.call_count, 4)
        self.assertIsInstance(result.result, EnrichmentError)
        self.assertEqual(self.task.status, "FAILURE")
        self.assertEqual(self.task.result, {"error": "Flight price provider request failed"})
        self.assertIsNotNone(self.task.completed_at)

    def test_client_error_fails_without_retry(self):
        _, client = self.run_task([provider_response(401)])
        self.assertEqual(client.get.call_count, 1)
        self.assertEqual(self.task.status, "FAILURE")
        self.assertNotIn("placeholder-key", str(self.task.result))

    def test_invalid_price_fails_without_retry(self):
        _, client = self.run_task([provider_response(payload={"best_flights": [{"price": -5}]})])
        self.assertEqual(client.get.call_count, 1)
        self.assertEqual(self.task.status, "FAILURE")
        self.assertIsNone(self.flight.retail_price)

    @override_settings(SERPAPI_KEY="")
    def test_missing_key_fails_before_any_request(self):
        _, client = self.run_task([])
        client.get.assert_not_called()
        self.assertEqual(self.task.result, {"error": "SERPAPI_KEY is not configured"})

    def test_unknown_flight_marks_task_failed(self):
        enrich_flight_task.apply(args=["missing"], task_id="fixture-task")
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "FAILURE")
        self.assertIn("missing", self.task.result["error"])
