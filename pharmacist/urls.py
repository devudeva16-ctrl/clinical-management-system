from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MedicineIssueViewSet, MedicineInventoryViewSet

router = DefaultRouter()
router.register(r'medicine-issues', MedicineIssueViewSet)
router.register(r'medicine-inventory', MedicineInventoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]