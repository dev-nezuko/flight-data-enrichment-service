from django.views.generic import ListView

from .models import EnrichmentTask, Flight


class TaskListView(ListView):
    template_name = "flights/task_list.html"
    context_object_name = "tasks"
    queryset = (
        EnrichmentTask.objects.filter(status__in=["SUCCESS", "FAILURE"])
        .select_related("flight")
        .order_by("-completed_at")[:3]
    )


class FlightListView(ListView):
    template_name = "flights/flight_list.html"
    context_object_name = "flights"
    queryset = Flight.objects.order_by("departure_time", "flight_id")
    paginate_by = 50
