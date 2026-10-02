from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('stations/', include('stations.urls')),
    path('bookings/', include('bookings.urls')),
    path('sessions/', include('sessions_app.urls')),
]