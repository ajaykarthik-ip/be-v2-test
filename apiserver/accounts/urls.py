from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_user, name='register'),
    path('test/', views.test_endpoint, name='test'),
    path('profile/', views.user_profile, name='user-profile'),
    path('change-password/', views.change_password, name='change-password'),
    path('login/', views.login_user, name='login'),
]