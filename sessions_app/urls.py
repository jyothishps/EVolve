from django.urls import path
from . import views

app_name = 'sessions_app'

urlpatterns = [
    path('start/<int:booking_id>/', views.session_start, name='session_start'),
    path('complete/<int:session_id>/', views.session_complete, name='session_complete'),
]
