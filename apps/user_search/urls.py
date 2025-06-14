from django.urls import path
from .views import searchForDataList, searchForDataDetail

urlpatterns = [
    path('data-list/', searchForDataList.as_view(), name='searchForDataList'),
    path('data-detail/', searchForDataDetail.as_view(), name='searchForDataDetail')
]
