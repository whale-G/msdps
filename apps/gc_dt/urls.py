from django.urls import path
from .views import GcProcess

urlpatterns = [
    path('api/gc-process/', GcProcess.as_view(), name='GcProcess'),
]
