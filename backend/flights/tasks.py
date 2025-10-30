from typing import Any

import httpx
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import EnrichmentTask, Flight
from .utils import extract_retail_price

PROVIDER_TIMEOUT_SECONDS = 30
RETRY_BASE_SECONDS = 60


class EnrichmentError(Exception):
    """A failure already recorded on the task row; retrying would not help."""


def is_transient(exc: httpx.HTTPError) -> bool:
    """Network faults, rate limits and provider 5xx are worth retrying; 4xx are not."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500
    return True


def build_search_params(flight: Flight, api_key: str) -> dict[str, Any]:
    return {
        "engine": "google_flights",
        "departure_id": flight.origin,
        "arrival_id": flight.destination,
        "outbound_date": flight.departure_time.strftime("%Y-%m-%d"),
        "type": 2,  # one-way; SerpApi would otherwise require a return_date
        "currency": "USD",
        "hl": "en",
        "api_key": api_key,
    }


def finish(task_id: str, status: str, result: dict[str, Any]) -> None:
    EnrichmentTask.objects.filter(task_id=task_id).update(
        status=status, result=result, completed_at=timezone.now()
    )


def fail(task_id: str, message: str) -> EnrichmentError:
    finish(task_id, "FAILURE", {"error": message})
    return EnrichmentError(message)


@shared_task(bind=True, max_retries=3)
def enrich_flight_task(self, flight_id: str) -> dict[str, Any]:
    task_id = self.request.id
    EnrichmentTask.objects.filter(task_id=task_id).update(status="STARTED")

    try:
        flight = Flight.objects.get(flight_id=flight_id)
    except Flight.DoesNotExist:
        raise fail(task_id, f"Flight with ID {flight_id} not found") from None

    if not settings.SERPAPI_KEY:
        raise fail(task_id, "SERPAPI_KEY is not configured")

    try:
        with httpx.Client(timeout=PROVIDER_TIMEOUT_SECONDS) as client:
            response = client.get(
                settings.SERPAPI_URL, params=build_search_params(flight, settings.SERPAPI_KEY)
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        if is_transient(exc) and self.request.retries < self.max_retries:
            raise self.retry(countdown=RETRY_BASE_SECONDS * 2**self.request.retries) from None
        # Provider URLs carry the API key, so the exception text is never stored.
        raise fail(task_id, "Flight price provider request failed") from None
    except ValueError:
        raise fail(task_id, "Flight price provider returned invalid JSON") from None

    try:
        retail_price = extract_retail_price(data)
    except ValueError:
        raise fail(task_id, "Flight price provider returned an invalid price") from None

    Flight.objects.filter(pk=flight.pk).update(
        retail_price=retail_price, enriched=retail_price is not None
    )
    result = {"retail_price": retail_price}
    if retail_price is None:
        result["detail"] = "No price in provider results"
    finish(task_id, "SUCCESS", result)
    return result
