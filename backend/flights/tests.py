# Standard library imports
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

# Third-party imports
import httpx
import pytest
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

# Local application imports
from .models import Flight, EnrichmentTask
from .tasks import enrich_flight_task
from .utils import extract_retail_price

class BaseTestCase(TestCase):
    def setUp(self):
        # Clear the database before each test
        Flight.objects.all().delete()
        EnrichmentTask.objects.all().delete()

class FlightModelTests(BaseTestCase):
    def setUp(self):
        super().setUp()  # Call parent's setUp to clear database
        self.flight_data = {
            "flight_id": "test-flight-1",
            "travel_class": "Business",
            "origin": "JFK",
            "destination": "ATH",
            "departure_time": timezone.now(),
            "arrival_time": timezone.now() + timedelta(hours=10),
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
                }
            ],
            "last_seen": timezone.now()
        }

    def test_flight_creation(self):
        flight = Flight.objects.create(**self.flight_data)
        self.assertEqual(flight.flight_id, self.flight_data["flight_id"])
        self.assertEqual(flight.travel_class, self.flight_data["travel_class"])
        self.assertEqual(flight.enriched, False)
        self.assertIsNone(flight.retail_price)

    def test_flight_str_representation(self):
        flight = Flight.objects.create(**self.flight_data)
        self.assertEqual(str(flight), self.flight_data["flight_id"])

class EnrichmentTaskModelTests(BaseTestCase):
    def setUp(self):
        super().setUp()  # Call parent's setUp to clear database
        self.flight = Flight.objects.create(
            flight_id="test-flight",
            travel_class="Economy",
            origin="JFK",
            destination="LAX",
            departure_time=timezone.now(),
            arrival_time=timezone.now() + timedelta(hours=6),
            flight_numbers=["AA123"],
            legs=[],
            last_seen=timezone.now()
        )

    def test_task_creation(self):
        task = EnrichmentTask.objects.create(
            task_id="test-task-id",
            flight=self.flight,
            status="PENDING"
        )
        self.assertEqual(task.status, "PENDING")
        self.assertIsNone(task.result)
        self.assertIsNotNone(task.created_at)
        self.assertIsNone(task.completed_at)

    def test_task_str_representation(self):
        task = EnrichmentTask.objects.create(
            task_id="test-task-id",
            flight=self.flight,
            status="PENDING"
        )
        self.assertEqual(str(task), "Task test-task-id - PENDING")

class FlightModelValidationTests(BaseTestCase):
    def setUp(self):
        super().setUp()  # Call parent's setUp to clear database
        self.valid_flight_data = {
            "flight_id": "test-flight-2",
            "travel_class": "Business",
            "origin": "JFK",
            "destination": "ATH",
            "departure_time": timezone.now(),
            "arrival_time": timezone.now() + timedelta(hours=10),
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
                }
            ],
            "last_seen": timezone.now()
        }

    def test_valid_flight_creation(self):
        flight = Flight.objects.create(**self.valid_flight_data)
        flight.full_clean()  # Validates all fields
        self.assertEqual(flight.flight_id, self.valid_flight_data["flight_id"])

class EnrichmentTaskLogicTests(BaseTestCase):
    def setUp(self):
        super().setUp()  # Call parent's setUp to clear database
        self.flight = Flight.objects.create(
            flight_id="test-flight",
            travel_class="Economy",
            origin="JFK",
            destination="LAX",
            departure_time=timezone.now(),
            arrival_time=timezone.now() + timedelta(hours=6),
            flight_numbers=["AA123"],
            legs=[{
                "origin": "JFK",
                "destination": "LAX",
                "departure_time": timezone.now().isoformat(),
                "arrival_time": (timezone.now() + timedelta(hours=6)).isoformat(),
                "flight_number": "AA123",
                "aircraft_type": "Boeing 737",
                "cabin_type": "Economy",
                "duration": 360,
                "layover_time": 0.0,
                "distance": 2475
            }],
            last_seen=timezone.now()
        )
        self.task = EnrichmentTask.objects.create(
            task_id="test-task-id",
            flight=self.flight,
            status="PENDING"
        )

    def test_task_result_storage(self):
        # Test storing valid result
        result = {"retail_price": 500.00}
        self.task.result = result
        self.task.save()
        self.assertEqual(self.task.result, result)

    def test_task_state_transitions(self):
        # Test PENDING to STARTED
        self.task.status = 'STARTED'
        self.task.save()
        self.assertEqual(self.task.status, 'STARTED')
        
        # Test STARTED to SUCCESS
        self.task.status = 'SUCCESS'
        self.task.completed_at = timezone.now()
        self.task.save()
        self.assertEqual(self.task.status, 'SUCCESS')
        self.assertIsNotNone(self.task.completed_at)

class ExtractRetailPriceTests(BaseTestCase):
    def test_empty_flights(self):
        data = {"best_flights": []}
        self.assertIsNone(extract_retail_price(data))

    def test_invalid_price_format(self):
        data = {"best_flights": [{"price": "invalid"}]}
        with self.assertRaises(ValueError):
            extract_retail_price(data)

    def test_missing_price(self):
        data = {"best_flights": [{}]}
        self.assertIsNone(extract_retail_price(data))

    def test_valid_price_extraction(self):
        data = {"best_flights": [{"price": 500.00}]}
        self.assertEqual(extract_retail_price(data), 500.00)

class EdgeCaseTests(BaseTestCase):
    def test_concurrent_task_creation(self):
        flight = Flight.objects.create(
            flight_id="test-flight",
            travel_class="Economy",
            origin="JFK",
            destination="LAX",
            departure_time=timezone.now(),
            arrival_time=timezone.now() + timedelta(hours=6),
            flight_numbers=["AA123"],
            legs=[],
            last_seen=timezone.now()
        )

        # Create multiple tasks for the same flight
        task1 = EnrichmentTask.objects.create(task_id="task1", flight=flight, status="PENDING")
        task2 = EnrichmentTask.objects.create(task_id="task2", flight=flight, status="PENDING")
        
        # Verify both tasks exist
        self.assertEqual(EnrichmentTask.objects.filter(flight=flight).count(), 2)
        
        # Update tasks concurrently
        task1.status = "SUCCESS"
        task1.save()
        task2.status = "FAILURE"
        task2.save()
        
        # Verify final states
        self.assertEqual(EnrichmentTask.objects.get(task_id="task1").status, "SUCCESS")
        self.assertEqual(EnrichmentTask.objects.get(task_id="task2").status, "FAILURE")

    def test_extreme_dates(self):
        flight_data = {
            "flight_id": "test-flight-3",
            "travel_class": "Economy",
            "origin": "JFK",
            "destination": "LAX",
            "departure_time": timezone.now() + timedelta(days=3650),  # 10 years in future
            "arrival_time": timezone.now() + timedelta(days=3650, hours=6),
            "flight_numbers": ["AA123"],
            "legs": [
                {
                    "origin": "JFK",
                    "destination": "LAX",
                    "departure_time": (timezone.now() + timedelta(days=3650)).isoformat(),
                    "arrival_time": (timezone.now() + timedelta(days=3650, hours=6)).isoformat(),
                    "flight_number": "AA123",
                    "aircraft_type": "Boeing 737",
                    "cabin_type": "Economy",
                    "duration": 360,
                    "layover_time": 0.0,
                    "distance": 2475
                }
            ],
            "last_seen": timezone.now()
        }
        flight = Flight.objects.create(**flight_data)
        flight.full_clean()

    def test_extreme_retail_prices(self):
        flight = Flight.objects.create(
            flight_id="test-flight-4",
            travel_class="Economy",
            origin="JFK",
            destination="LAX",
            departure_time=timezone.now(),
            arrival_time=timezone.now() + timedelta(hours=6),
            flight_numbers=["AA123"],
            legs=[{
                "origin": "JFK",
                "destination": "LAX",
                "departure_time": timezone.now().isoformat(),
                "arrival_time": (timezone.now() + timedelta(hours=6)).isoformat(),
                "flight_number": "AA123",
                "aircraft_type": "Boeing 737",
                "cabin_type": "Economy",
                "duration": 360,
                "layover_time": 0.0,
                "distance": 2475
            }],
            last_seen=timezone.now()
        )

        # Test maximum allowed price
        flight.retail_price = Decimal('99999999.99')
        flight.full_clean()

    def test_unicode_airport_codes(self):
        flight_data = {
            "flight_id": "test-flight",
            "travel_class": "Economy",
            "origin": "羽田",  # Japanese characters
            "destination": "LAX",
            "departure_time": timezone.now(),
            "arrival_time": timezone.now() + timedelta(hours=6),
            "flight_numbers": ["AA123"],
            "legs": [],
            "last_seen": timezone.now()
        }
        with self.assertRaises(ValidationError):
            flight = Flight.objects.create(**flight_data)
            flight.full_clean()

    def test_very_long_flight_id(self):
        flight_data = {
            "flight_id": "x" * 100,  # Max length is 100
            "travel_class": "Economy",
            "origin": "JFK",
            "destination": "LAX",
            "departure_time": timezone.now(),
            "arrival_time": timezone.now() + timedelta(hours=6),
            "flight_numbers": ["AA123"],
            "legs": [
                {
                    "origin": "JFK",
                    "destination": "LAX",
                    "departure_time": timezone.now().isoformat(),
                    "arrival_time": (timezone.now() + timedelta(hours=6)).isoformat(),
                    "flight_number": "AA123",
                    "aircraft_type": "Boeing 737",
                    "cabin_type": "Economy",
                    "duration": 360,
                    "layover_time": 0.0,
                    "distance": 2475
                }
            ],
            "last_seen": timezone.now()
        }
        flight = Flight.objects.create(**flight_data)
        flight.full_clean()

        # Test exceeding max length
        with self.assertRaises(ValidationError):
            flight.flight_id = "x" * 101
            flight.full_clean()
