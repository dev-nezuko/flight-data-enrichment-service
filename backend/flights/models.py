from django.db import models


class Flight(models.Model):
    flight_id = models.CharField(max_length=100, unique=True)  # matches input "id"
    travel_class = models.CharField(max_length=50)
    origin = models.CharField(max_length=10)
    destination = models.CharField(max_length=10)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    flight_numbers = models.JSONField()  # List of strings
    legs = models.JSONField(blank=True)  # list of leg dicts; may be empty
    last_seen = models.DateTimeField()

    retail_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    enriched = models.BooleanField(default=False)

    def __str__(self):
        return self.flight_id


class EnrichmentTask(models.Model):
    task_id = models.CharField(max_length=255, unique=True)
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE)
    # PENDING, STARTED, SUCCESS or FAILURE, written by the API and the worker
    status = models.CharField(max_length=20, default="PENDING")
    result = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Task {self.task_id} - {self.status}"
