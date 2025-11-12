from datetime import datetime, timezone
from unittest.mock import patch, Mock
from django.test import TestCase
from flights.utils import extract_retail_price
from flights.models import Flight, EnrichmentTask
from flights.tasks import enrich_flight_task


class PriceSafetyTests(TestCase):
    def test_invalid_numeric_prices(self):
        for price in [True, -1, 'NaN', 'Infinity']:
            with self.subTest(price=price), self.assertRaises(ValueError):
                extract_retail_price({'best_flights': [{'price': price}]})

    def test_mocked_one_way_search_and_result_storage(self):
        departure = datetime(2027, 1, 2, 10, tzinfo=timezone.utc)
        flight = Flight.objects.create(flight_id='synthetic', travel_class='Economy', origin='JFK', destination='LAX', departure_time=departure, arrival_time=departure, flight_numbers=['DEMO1'], legs=[], last_seen=departure)
        task = EnrichmentTask.objects.create(task_id='synthetic-task', flight=flight, status='PENDING')
        response = Mock()
        response.json.return_value = {'best_flights': [{'price': 123.45}]}
        with patch('flights.tasks.httpx.Client') as client:
            client.return_value.__enter__.return_value.get.return_value = response
            result = enrich_flight_task.apply(args=[flight.flight_id], task_id=task.task_id, throw=True)
            params = client.return_value.__enter__.return_value.get.call_args.kwargs['params']
            self.assertEqual(params['type'], 2)
            self.assertNotIn('return_date', params)
            self.assertEqual(result.result, {'retail_price': 123.45})
        task.refresh_from_db()
        self.assertEqual(task.status, 'SUCCESS')
        self.assertIsNotNone(task.completed_at)


class EnqueueSafetyTests(TestCase):
    def payload(self):
        return {'id': 'synthetic-api-flight', 'travel_class': 'Economy', 'origin': 'JFK', 'destination': 'LAX', 'departure_time': '2027-01-02T10:00:00Z', 'arrival_time': '2027-01-02T16:00:00Z', 'flight_numbers': ['DEMO1'], 'legs': [], 'last_seen': '2027-01-01T00:00:00Z'}

    def test_enqueues_with_matching_task_identifier(self):
        from api.main import enrich_flight
        from api.validation_models import FlightData
        with patch('api.main.enrich_flight_task.apply_async') as enqueue:
            enqueue.side_effect = lambda **kwargs: Mock(id=kwargs['task_id'])
            response = enrich_flight(FlightData(**self.payload()))
        self.assertEqual(response['status'], 'PENDING')
        self.assertTrue(EnrichmentTask.objects.filter(task_id=response['task_id'], status='PENDING').exists())

    def test_queue_failure_is_not_left_pending(self):
        from fastapi import HTTPException
        from api.main import enrich_flight
        from api.validation_models import FlightData
        with patch('api.main.enrich_flight_task.apply_async', side_effect=RuntimeError('private broker diagnostic')):
            with self.assertRaises(HTTPException) as raised:
                enrich_flight(FlightData(**self.payload()))
        self.assertEqual(raised.exception.status_code, 503)
        task = EnrichmentTask.objects.get(flight__flight_id='synthetic-api-flight')
        self.assertEqual(task.status, 'FAILURE')
        self.assertNotIn('private broker', str(task.result))
