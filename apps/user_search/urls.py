from django.urls import path
from .views import searchForDataList, searchForDataDetail, dataProcessStatistics

urlpatterns = [
    path('data-list/', searchForDataList.as_view(), name='searchForDataList'),
    path('data-detail/', searchForDataDetail.as_view(), name='searchForDataDetail'),
    path('data-process-statistics/', dataProcessStatistics.as_view(), name='dataProcessStatistics')
]
