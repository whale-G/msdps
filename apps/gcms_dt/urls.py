from django.urls import path
from .views import GcmsProcessShimazu, GcmsProcessThermo
from .views import GcmsProcessShimazuStatus, GcmsProceeThermoStatus

urlpatterns = [
    path('api/gcms-process/shimazu/', GcmsProcessShimazu.as_view(), name='GcmsProcessShimazu'),
    path('api/gcms-status/shimazu/', GcmsProcessShimazuStatus.as_view(), name='GcmsProcessShimazuStatus'),
    path('api/gcms-process/thermo/', GcmsProcessThermo.as_view(), name='GcmsProcessThermo'),
    path('api/gcms-status/thermo/', GcmsProceeThermoStatus.as_view(), name='GcmsProceeThermoStatus')
]
