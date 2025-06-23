from django.urls import path
from .views import LcProcessShimazu, LcProcessAgilent
from .views import LcProcessShimazuStatus, LcProcessAailentStatus

urlpatterns = [
    path('api/lc-process/shimazu/', LcProcessShimazu.as_view(), name='LcProcessShimazu'),
    path('api/lc-status/shimazu/', LcProcessShimazuStatus.as_view(), name='LcProcessShimazuStatus'),
    path('api/lc-process/agilent/', LcProcessAgilent.as_view(), name='LcProcessAgilent'),
    path('api/lc-status/agilent/', LcProcessAailentStatus.as_view(), name='LcProcessAailentStatus')
]
