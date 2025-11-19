from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from .models import LabReport, LabEquipment
from .serializers import LabReportSerializer, LabEquipmentSerializer
from rest_framework.permissions import IsAuthenticated
class LabReportViewSet(viewsets.ModelViewSet):
    queryset = LabReport.objects.all()
    serializer_class = LabReportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = LabReport.objects.all()
        technician_id = self.request.query_params.get('technician_id')
        status = self.request.query_params.get('status')
        priority = self.request.query_params.get('priority')
        result_status = self.request.query_params.get('result_status')
        is_critical = self.request.query_params.get('is_critical')
        
        if technician_id: queryset = queryset.filter(technician_id=technician_id)
        if status: queryset = queryset.filter(status=status)
        if priority: queryset = queryset.filter(priority=priority)
        if result_status: queryset = queryset.filter(result_status=result_status)
        if is_critical: queryset = queryset.filter(is_critical_result=(is_critical.lower() == 'true'))
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        lab_report = self.get_object()
        lab_report.status = 'COMPLETED'
        lab_report.completed_date = timezone.now()
        lab_report.save()
        return Response({'status': 'Lab report marked as completed'})
    
    @action(detail=True, methods=['post'])
    def mark_in_progress(self, request, pk=None):
        lab_report = self.get_object()
        lab_report.status = 'IN_PROGRESS'
        lab_report.save()
        return Response({'status': 'Lab report marked as in progress'})
    
    @action(detail=True, methods=['post'])
    def mark_critical_acknowledged(self, request, pk=None):
        lab_report = self.get_object()
        acknowledged_by = request.data.get('acknowledged_by')
        if not acknowledged_by:
            return Response({'error': 'acknowledged_by is required'}, status=status.HTTP_400_BAD_REQUEST)
        lab_report.mark_critical_acknowledged(acknowledged_by)
        return Response({'status': 'Critical result acknowledged'})
    
    @action(detail=False, methods=['get'])
    def pending_reports(self, request):
        pending_reports = LabReport.objects.filter(status__in=['PENDING', 'IN_PROGRESS'])
        serializer = self.get_serializer(pending_reports, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def critical_results(self, request):
        critical_reports = LabReport.objects.filter(is_critical_result=True, critical_result_acknowledged=False)
        serializer = self.get_serializer(critical_reports, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue_reports(self, request):
        overdue_reports = [report for report in LabReport.objects.filter(status__in=['PENDING', 'IN_PROGRESS']) if report.is_overdue()]
        serializer = self.get_serializer(overdue_reports, many=True)
        return Response(serializer.data)

class LabEquipmentViewSet(viewsets.ModelViewSet):
    queryset = LabEquipment.objects.all()
    serializer_class = LabEquipmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = LabEquipment.objects.all()
        status = self.request.query_params.get('status')
        needs_calibration = self.request.query_params.get('needs_calibration')
        needs_maintenance = self.request.query_params.get('needs_maintenance')
        
        if status: queryset = queryset.filter(status=status)
        if needs_calibration == 'true': queryset = queryset.filter(calibration_due_date__lte=timezone.now().date())
        if needs_maintenance == 'true': queryset = queryset.filter(next_maintenance_date__lte=timezone.now().date())
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def mark_operational(self, request, pk=None):
        equipment = self.get_object()
        equipment.status = 'OPERATIONAL'
        equipment.save()
        return Response({'status': 'Equipment marked as operational'})
    
    @action(detail=True, methods=['post'])
    def mark_maintenance(self, request, pk=None):
        equipment = self.get_object()
        equipment.status = 'MAINTENANCE'
        equipment.save()
        return Response({'status': 'Equipment marked as under maintenance'})
    
    @action(detail=True, methods=['post'])
    def update_calibration(self, request, pk=None):
        equipment = self.get_object()
        calibration_date = request.data.get('calibration_date')
        if calibration_date:
            equipment.last_calibration_date = calibration_date
        equipment.status = 'OPERATIONAL'
        equipment.save()
        return Response({'status': 'Calibration updated'})
    
    @action(detail=False, methods=['get'])
    def maintenance_due(self, request):
        due_equipment = LabEquipment.objects.filter(next_maintenance_date__lte=timezone.now().date())
        serializer = self.get_serializer(due_equipment, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def calibration_due(self, request):
        due_equipment = LabEquipment.objects.filter(calibration_due_date__lte=timezone.now().date())
        serializer = self.get_serializer(due_equipment, many=True)
        return Response(serializer.data)