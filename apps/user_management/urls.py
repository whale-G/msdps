from django.urls import path
from .views import UserRegister, UserLogin, ChangePassword

urlpatterns = [
    path('register/', UserRegister.as_view(), name='UserRegister'),
    path('login/', UserLogin.as_view(), name='UserLogin'),
    path('changepw/', ChangePassword.as_view(), name='ChangePassword'),
]