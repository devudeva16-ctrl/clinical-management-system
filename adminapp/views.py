from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Staff
from .serializers import StaffSerializer
from rest_framework.permissions import IsAuthenticated

class StaffViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.all()
    serializer_class = StaffSerializer
    permission_classes = [IsAuthenticated]

    
    def get_queryset(self):
        queryset = Staff.objects.all()
        role = self.request.query_params.get('role')
        is_active = self.request.query_params.get('is_active')
        if role: queryset = queryset.filter(role=role)
        if is_active: queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset
    
    @action(detail=True, methods=['post'])
    def set_password(self, request, pk=None):
        staff = self.get_object()
        password = request.data.get('password')
        if not password: return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            staff.set_password(password)
            staff.save()
            return Response({'status': 'password set'})
        except (ValidationError, DjangoValidationError) as e: return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        staff = self.get_object()
        if not staff.is_active: return Response({'error': 'Staff is already inactive'}, status=status.HTTP_400_BAD_REQUEST)
        staff.is_active = False
        staff.save()
        return Response({'status': 'staff deactivated'})
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        staff = self.get_object()
        if staff.is_active: return Response({'error': 'Staff is already active'}, status=status.HTTP_400_BAD_REQUEST)
        staff.is_active = True
        staff.save()
        return Response({'status': 'staff activated'})
    
    @action(detail=False, methods=['get'])
    def roles(self, request):
        roles = [{'value': choice[0], 'label': choice[1]} for choice in Staff.ROLE_CHOICES]
        return Response(roles)