from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.RoleBasedLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.driver_dashboard, name='driver_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Station management (Admin)
    path('manage/stations/', views.station_list, name='station_list'),
    path('manage/stations/add/', views.station_add, name='station_add'),
    path('manage/stations/<int:station_id>/edit/', views.station_edit, name='station_edit'),
    path('manage/stations/<int:station_id>/delete/', views.station_delete, name='station_delete'),

    # Charger management (Admin)
    path('manage/chargers/', views.charger_list, name='charger_list'),
    path('manage/chargers/add/', views.charger_add, name='charger_add'),
    path('manage/chargers/<int:charger_id>/edit/', views.charger_edit, name='charger_edit'),
    path('manage/chargers/<int:charger_id>/delete/', views.charger_delete, name='charger_delete'),

    # Driver station map
    path('stations/map/view/', views.driver_station_map, name='driver_station_map'),
]