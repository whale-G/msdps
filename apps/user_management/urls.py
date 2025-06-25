from django.urls import path
from .views import UserRegister, UserLogin, ChangePassword
from .views import UserListView, UserCreateView, UserDeleteView, UserUpdateView

urlpatterns = [
    path('register/', UserRegister.as_view(), name='UserRegister'),
    path('login/', UserLogin.as_view(), name='UserLogin'),
    path('changepw/', ChangePassword.as_view(), name='ChangePassword'),
    path('admin/users/', UserListView.as_view(), name='UserListView'),
    path('admin/users/create/', UserCreateView.as_view(), name='UserCreateView'),
    path('admin/users/<uuid:uuid>/delete/', UserDeleteView.as_view(), name='UserDeleteView'),
    path('admin/users/<uuid:uuid>/update/', UserUpdateView.as_view(), name='UserUpdateView')
]
