from django.urls import path
from . import views

app_name = 'sessions_app'

urlpatterns = [
    path('', views.session_list, name='session_list'),
    path('<int:session_id>/', views.session_detail, name='session_detail'),
    path('start/<int:booking_id>/', views.session_start, name='session_start'),
    path('complete/<int:session_id>/', views.session_complete, name='session_complete'),
    path('<int:session_id>/mark-paid/', views.session_mark_paid, name='session_mark_paid'),
]
