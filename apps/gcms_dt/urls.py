from django.urls import path
from .views import GcmsProcessShimazu, GcmsProcessThermo

urlpatterns = [
    path('api/gcms-process/shimazu/', GcmsProcessShimazu.as_view(), name='GcmsProcessShimazu'),
    path('api/gcms-process/thermo/', GcmsProcessThermo.as_view(), name='GcmsProcessThermo'),
]
