from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LabReportViewSet, LabEquipmentViewSet

router = DefaultRouter()
router.register(r'lab-reports', LabReportViewSet)
router.register(r'lab-equipment', LabEquipmentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]