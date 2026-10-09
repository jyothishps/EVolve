from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('', views.booking_list, name='booking_list'),
    path('create/<int:slot_id>/', views.booking_create, name='booking_create'),
    path('<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('<int:booking_id>/cancel/', views.booking_cancel, name='booking_cancel'),
    path('manage/', views.admin_booking_list, name='admin_booking_list'),
    path('<int:booking_id>/check-in/', views.booking_checkin, name='booking_checkin'),
    path('manage/<int:booking_id>/cancel/', views.admin_booking_cancel, name='admin_booking_cancel'),
]
