from django.urls import path
from . import views

urlpatterns = [
    path('tasks/', views.TaskListView.as_view(), name='task-list'),
    path('', views.FlightListView.as_view(), name='flight-list'),
]
