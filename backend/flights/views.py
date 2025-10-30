from django.shortcuts import render

# Create your views here.
from django.views.generic import ListView
from .models import EnrichmentTask, Flight

class TaskListView(ListView):
    model = EnrichmentTask
    template_name = 'flights/task_list.html'
    context_object_name = 'tasks'
    queryset = EnrichmentTask.objects.filter(status__in=['SUCCESS', 'FAILURE']).order_by('-completed_at')[:3]

class FlightListView(ListView):
    model = Flight
    template_name = 'flights/flight_list.html'
    context_object_name = 'flights'
    # Only show key columns - you can filter in template
