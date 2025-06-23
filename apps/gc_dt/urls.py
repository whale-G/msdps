from django.urls import path
from .views import GcProcess, GcProcessStatus

urlpatterns = [
    path('api/gc-process/', GcProcess.as_view(), name='gc_process'),
    path('api/gc-status/', GcProcessStatus.as_view(), name='gc_process_status'),
]
