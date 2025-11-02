from django.contrib import admin

from flights.models import Flight,EnrichmentTask

admin.site.register(Flight)
admin.site.register(EnrichmentTask)
