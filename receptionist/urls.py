# receptionist branch update - testing commit
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'patients', views.PatientViewSet)
router.register(r'appointments', views.AppointmentViewSet)
router.register(r'billing', views.BillingViewSet, basename='billing')

urlpatterns = [
    path('', include(router.urls)),
]