from django.contrib import admin

from flights.models import EnrichmentTask, Flight

admin.site.register(Flight)
admin.site.register(EnrichmentTask)
