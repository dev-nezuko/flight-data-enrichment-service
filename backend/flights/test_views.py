from datetime import UTC, datetime, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from flights.models import EnrichmentTask, Flight

DEPARTURE = datetime(2027, 5, 6, 8, tzinfo=UTC)


def make_flight(flight_id, departure=DEPARTURE, **fields):
    return Flight.objects.create(
        flight_id=flight_id,
        travel_class="Economy",
        origin="JFK",
        destination="LAX",
        departure_time=departure,
        arrival_time=departure + timedelta(hours=6),
        flight_numbers=["DEMO1"],
        legs=[],
        last_seen=departure,
        **fields,
    )


class FlightListViewTests(TestCase):
    def test_empty_state(self):
        response = self.client.get(reverse("flight-list"))
        self.assertContains(response, "No flights found.")

    def test_zero_price_is_shown_not_hidden(self):
        make_flight("free-fare", retail_price=Decimal("0.00"), enriched=True)
        make_flight("unpriced")
        response = self.client.get(reverse("flight-list"))
        self.assertContains(response, '<td class="num">0.00</td>', html=True)
        self.assertContains(response, '<td class="num">N/A</td>', html=True)

    def test_flights_are_ordered_by_departure(self):
        make_flight("later", DEPARTURE + timedelta(days=1))
        make_flight("earlier")
        flights = list(self.client.get(reverse("flight-list")).context["flights"])
        self.assertEqual([f.flight_id for f in flights], ["earlier", "later"])


class TaskListViewTests(TestCase):
    def test_shows_only_three_latest_completed(self):
        flight = make_flight("f")
        EnrichmentTask.objects.create(task_id="pending", flight=flight)
        for i in range(4):
            EnrichmentTask.objects.create(
                task_id=f"done-{i}",
                flight=flight,
                status="SUCCESS",
                completed_at=DEPARTURE + timedelta(minutes=i),
            )
        tasks = list(self.client.get(reverse("task-list")).context["tasks"])
        self.assertEqual([t.task_id for t in tasks], ["done-3", "done-2", "done-1"])
