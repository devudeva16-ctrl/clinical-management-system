"""
URL configuration for CMS project.

The urlpatterns list routes URLs to views.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),

    # JWT Authentication
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # App URLs
    path('adminapp/', include('adminapp.urls')),
    path('receptionist/', include('receptionist.urls')),
    path('doctor/', include('doctor.urls')),
    path('pharmacist/', include('pharmacist.urls')),
    path('labtechnician/', include('labtechnician.urls')),
    path('billing/', include('billing.urls')),
]