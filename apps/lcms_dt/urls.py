from django.urls import path
from .views import LcmsProcessAb, LcmsProcessAgilent
from .views import LcmsProcessAbStatus, LcmsProcessAgilentStatus

urlpatterns = [
    path('api/lcms-process/ab/', LcmsProcessAb.as_view(), name='LcmsProcessAb'),
    path('api/lcms-status/ab/', LcmsProcessAbStatus.as_view(), name='LcmsProcessAbStatus'),
    path('api/lcms-process/agilent/', LcmsProcessAgilent.as_view(), name='LcmsProcessAgilent'),
    path('api/lcms-status/agilent/', LcmsProcessAgilentStatus.as_view(), name="LcmsProcessAgilentStatus")
]
