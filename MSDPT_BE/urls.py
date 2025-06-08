"""
URL configuration for MSDPT_BE project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("gc_dt/", include("apps.gc_dt.urls")),
    path("gcms_dt/", include("apps.gcms_dt.urls")),
    path("lc_dt/", include("apps.lc_dt.urls")),
    path("lcms_dt/", include("apps.lcms_dt.urls")),
    path("user_management/", include("apps.user_management.urls")),
    path("search/", include("apps.user_search.urls"))
]
