from django.urls import path
from .views import LcmsProcessAjl, LcmsProcessAb

urlpatterns = [
    path('api/lcms-process/ab/', LcmsProcessAb.as_view(), name='LcmsProcessAb'),
    path('api/lcms-process/ajl/', LcmsProcessAjl.as_view(), name='LcmsProcessAjl'),
]
