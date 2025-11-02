# Standard library imports
import os
from typing import Dict, Any

# Third-party imports
import httpx
from celery import shared_task
from django.utils import timezone
from dotenv import load_dotenv
from pathlib import Path

# Local application imports
from .models import Flight, EnrichmentTask

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(env_path)

from backend.settings import SERPAPI_KEY
from flights.utils import extract_retail_price



@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    retry_backoff=True
)
def enrich_flight_task(self, flight_id: str) -> Dict[str, Any]:
    """
    Enrich flight data with retail price information.
    
    Args:
        flight_id: The ID of the flight to enrich
        
    Returns:
        Dict containing the retail price or error information
        
    Raises:
        Flight.DoesNotExist: If flight is not found
        MaxRetriesExceededError: If all retries are exhausted
        ValueError: If API response is invalid
    """
    try:
        # Get flight data
        flight = Flight.objects.get(flight_id=flight_id)
        task_obj = EnrichmentTask.objects.get(task_id=self.request.id)
        
        # Update task status to started
        task_obj.status = 'STARTED'
        task_obj.save()

        # Prepare API request parameters
        params = {
            "engine": "google_flights",
            "departure_id": flight.origin,
            "arrival_id": flight.destination,
            "outbound_date": flight.departure_time.strftime("%Y-%m-%d"),
            "return_date": flight.arrival_time.strftime("%Y-%m-%d"),
            "currency": "USD",
            "hl": "en",
            "api_key": SERPAPI_KEY
        }

        # Make API request with timeout and retries
        with httpx.Client(timeout=200) as client:
            response = client.get("https://serpapi.com/search.json", params=params)
            response.raise_for_status()
            data = response.json()

        # Extract and validate retail price
        retail_price = extract_retail_price(data)

        # Update flight data
        if retail_price is not None:
            flight.retail_price = retail_price
        flight.enriched = True
        flight.save()

        # Update task status
        task_obj.status = 'SUCCESS'
        task_obj.result = {"retail_price": retail_price}
        task_obj.completed_at = timezone.now()
        task_obj.save()

        return {"retail_price": retail_price}

    except Flight.DoesNotExist:
        error_msg = f"Flight with ID {flight_id} not found"
        task_obj = EnrichmentTask.objects.get(task_id=self.request.id)
        task_obj.status = 'FAILURE'
        task_obj.result = {"error": error_msg}
        task_obj.completed_at = timezone.now()
        task_obj.save()
        raise

    except httpx.HTTPError as e:
        error_msg = f"HTTP error occurred: {str(e)}"
        if self.request.retries >= self.max_retries:
            task_obj = EnrichmentTask.objects.get(task_id=self.request.id)
            task_obj.status = 'FAILURE'
            task_obj.result = {"error": error_msg}
            task_obj.completed_at = timezone.now()
            task_obj.save()
        raise

    except Exception as e:
        error_msg = f"Error enriching flight data: {str(e)}"
        task_obj = EnrichmentTask.objects.get(task_id=self.request.id)
        task_obj.status = 'FAILURE'
        task_obj.result = {"error": error_msg}
        task_obj.completed_at = timezone.now()
        task_obj.save()
        raise
