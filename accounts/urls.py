from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.RoleBasedLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.driver_dashboard, name='driver_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
]
