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

    # Station management
    path('manage/stations/', views.station_list, name='station_list'),
    path('manage/stations/add/', views.station_add, name='station_add'),
    path('manage/stations/<int:station_id>/edit/', views.station_edit, name='station_edit'),
    path('manage/stations/<int:station_id>/delete/', views.station_delete, name='station_delete'),

    # Charger management
    path('manage/chargers/', views.charger_list, name='charger_list'),
    path('manage/chargers/add/', views.charger_add, name='charger_add'),
    path('manage/chargers/<int:charger_id>/edit/', views.charger_edit, name='charger_edit'),
    path('manage/chargers/<int:charger_id>/delete/', views.charger_delete, name='charger_delete'),

    # Slot management
    path('manage/slots/', views.slot_list, name='slot_list'),
    path('manage/slots/add/', views.slot_add, name='slot_add'),
    path('manage/slots/<int:slot_id>/edit/', views.slot_edit, name='slot_edit'),
    path('manage/slots/<int:slot_id>/delete/', views.slot_delete, name='slot_delete'),

    # Driver station browsing
    path('stations/', views.driver_station_list, name='driver_station_list'),
    path('stations/<int:station_id>/', views.driver_station_detail, name='driver_station_detail'),
    path('stations/map/view/', views.driver_station_map, name='driver_station_map'),

        # Booking - driver
    path('bookings/create/<int:slot_id>/', views.booking_create, name='booking_create'),
    path('bookings/', views.booking_list, name='booking_list'),
    path('bookings/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('bookings/<int:booking_id>/cancel/', views.booking_cancel, name='booking_cancel'),

    # Booking - admin
    path('manage/bookings/', views.admin_booking_list, name='admin_booking_list'),
    path('manage/bookings/<int:booking_id>/update/', views.admin_booking_update_status, name='admin_booking_update_status'),
]