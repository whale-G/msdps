from django.urls import path
from .views import LcProcessShimazu, LcProcessAjl

urlpatterns = [
    path('api/lc-process/shimazu/', LcProcessShimazu.as_view(), name='LcProcessShimazu'),
    path('api/lc-process/ajl/', LcProcessAjl.as_view(), name='LcProcessAjl'),
]
