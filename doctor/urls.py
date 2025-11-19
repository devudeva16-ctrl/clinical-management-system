# doctor/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DoctorAppointmentViewSet,
    DiagnosisViewSet,
    PrescriptionViewSet,
    LabRequestViewSet
)

router = DefaultRouter()
router.register(r'appointments', DoctorAppointmentViewSet, basename='doctor-appointments')
router.register(r'diagnoses', DiagnosisViewSet, basename='doctor-diagnoses')
router.register(r'prescriptions', PrescriptionViewSet, basename='doctor-prescriptions')
router.register(r'lab-requests', LabRequestViewSet, basename='doctor-lab-requests')

urlpatterns = [
    path('', include(router.urls)),
]