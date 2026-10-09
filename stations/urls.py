from django.urls import path
from . import views

app_name = 'stations'

urlpatterns = [
    # Driver station browsing & map
    path('', views.driver_station_list, name='driver_station_list'),
    path('<int:station_id>/', views.driver_station_detail, name='driver_station_detail'),
    path('map/', views.driver_station_map, name='driver_station_map'),

    # Station management (Admin)
    path('manage/', views.station_list, name='station_list'),
    path('manage/add/', views.station_add, name='station_add'),
    path('manage/<int:station_id>/edit/', views.station_edit, name='station_edit'),
    path('manage/<int:station_id>/delete/', views.station_delete, name='station_delete'),

    # Charger management (Admin)
    path('chargers/', views.charger_list, name='charger_list'),
    path('chargers/add/', views.charger_add, name='charger_add'),
    path('chargers/<int:charger_id>/edit/', views.charger_edit, name='charger_edit'),
    path('chargers/<int:charger_id>/delete/', views.charger_delete, name='charger_delete'),

    # Slot management (Admin)
    path('slots/', views.slot_list, name='slot_list'),
    path('manage/slots/', views.slot_list),
    path('slots/add/', views.slot_add, name='slot_add'),
    path('slots/<int:slot_id>/edit/', views.slot_edit, name='slot_edit'),
    path('slots/<int:slot_id>/delete/', views.slot_delete, name='slot_delete'),
    path('slots/<int:slot_id>/reopen/', views.slot_reopen, name='slot_reopen'),
]
