from django.urls import path
from .views import searchByUser

urlpatterns = [
    path('', searchByUser.as_view(), name='searchByUser')
]
