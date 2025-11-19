# doctor/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from datetime import date, datetime, timedelta

from receptionist.models import Appointment, Patient
from adminapp.models import Staff
from .models import Diagnosis, Prescription, LabRequest
from .serializers import (
    DoctorAppointmentSerializer,
    DiagnosisSerializer,
    PrescriptionSerializer, 
    LabRequestSerializer
)

class DoctorAppointmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for doctors to view their appointments from receptionist
    """
    serializer_class = DoctorAppointmentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'put', 'post']  # Remove delete
    
    def get_queryset(self):
        """
        Return appointments for doctors
        """
        print("DEBUG - Getting appointments for doctor...")
        
        # Get all appointments first
        queryset = Appointment.objects.all()
        print(f"DEBUG - Total appointments in system: {queryset.count()}")
        
        # Try to filter by doctor if possible
        try:
            doctors = Staff.objects.filter(role='DOCTOR')
            if doctors.exists():
                doctor_staff = doctors.first()
                queryset = queryset.filter(doctor=doctor_staff)
                print(f"DEBUG - Filtered by doctor: {doctor_staff.full_name}")
            else:
                print("DEBUG - No doctors found, showing all appointments")
        except Exception as e:
            print(f"DEBUG - Error filtering by doctor: {e}")
        
        # Apply URL filters
        status_filter = self.request.query_params.get('status')
        date_filter = self.request.query_params.get('date')
        priority_filter = self.request.query_params.get('priority')
        patient_name = self.request.query_params.get('patient_name')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            print(f"DEBUG - Filtered by status: {status_filter}")
        if date_filter:
            queryset = queryset.filter(appointment_date=date_filter)
            print(f"DEBUG - Filtered by date: {date_filter}")
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
            print(f"DEBUG - Filtered by priority: {priority_filter}")
        if patient_name:
            queryset = queryset.filter(patient__name__icontains=patient_name)
            print(f"DEBUG - Filtered by patient name: {patient_name}")
        
        print(f"DEBUG - Final result: {queryset.count()} appointments")
        return queryset.select_related('patient', 'doctor').order_by('appointment_date', 'appointment_time')
    
    @action(detail=False, methods=['get'])
    def todays_appointments(self, request):
        """Get today's appointments for the doctor"""
        queryset = self.get_queryset().filter(appointment_date=date.today())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming_appointments(self, request):
        """Get upcoming appointments (next 7 days)"""
        start_date = date.today()
        end_date = start_date + timedelta(days=7)
        
        queryset = self.get_queryset().filter(
            appointment_date__range=[start_date, end_date],
            status__in=['SCHEDULED', 'CONFIRMED']
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_appointments(self, request):
        """Get pending appointments (scheduled and confirmed)"""
        queryset = self.get_queryset().filter(
            status__in=['SCHEDULED', 'CONFIRMED']
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def start_consultation(self, request, pk=None):
        """Mark appointment as in progress"""
        appointment = self.get_object()
        
        if appointment.status in ['SCHEDULED', 'CONFIRMED']:
            appointment.status = 'IN_PROGRESS'
            appointment.check_in_time = timezone.now()
            appointment.save()
            
            serializer = self.get_serializer(appointment)
            return Response({
                'status': 'Consultation started',
                'appointment': serializer.data
            })
        
        return Response(
            {'error': 'Cannot start consultation for this appointment status'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def complete_consultation(self, request, pk=None):
        """Mark appointment as completed"""
        appointment = self.get_object()
        actual_duration = request.data.get('actual_duration')
        
        if appointment.status == 'IN_PROGRESS':
            appointment.status = 'COMPLETED'
            if actual_duration:
                appointment.actual_duration = actual_duration
            appointment.check_out_time = timezone.now()
            appointment.save()
            
            serializer = self.get_serializer(appointment)
            return Response({
                'status': 'Consultation completed',
                'appointment': serializer.data
            })
        
        return Response(
            {'error': 'Cannot complete consultation that is not in progress'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update appointment status"""
        appointment = self.get_object()
        new_status = request.data.get('status')
        
        valid_statuses = ['SCHEDULED', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']
        
        if new_status in valid_statuses:
            appointment.status = new_status
            appointment.save()
            
            serializer = self.get_serializer(appointment)
            return Response({
                'status': f'Appointment status updated to {new_status}',
                'appointment': serializer.data
            })
        
        return Response(
            {'error': 'Invalid status'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get appointment statistics for the doctor"""
        queryset = self.get_queryset()
        
        total_appointments = queryset.count()
        todays_appointments = queryset.filter(appointment_date=date.today()).count()
        
        stats = {
            'total_appointments': total_appointments,
            'todays_appointments': todays_appointments,
            'scheduled': queryset.filter(status='SCHEDULED').count(),
            'confirmed': queryset.filter(status='CONFIRMED').count(),
            'in_progress': queryset.filter(status='IN_PROGRESS').count(),
            'completed': queryset.filter(status='COMPLETED').count(),
            'cancelled': queryset.filter(status='CANCELLED').count(),
            'urgent_cases': queryset.filter(priority='URGENT').count(),
        }
        
        return Response(stats)

class DiagnosisViewSet(viewsets.ModelViewSet):
    queryset = Diagnosis.objects.all()
    serializer_class = DiagnosisSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter diagnoses by current doctor"""
        user = self.request.user
        
        try:
            # Try to get current user's doctor profile
            doctors = Staff.objects.filter(role='DOCTOR')
            if doctors.exists():
                doctor_staff = doctors.first()
                queryset = Diagnosis.objects.filter(doctor=doctor_staff)
            else:
                queryset = Diagnosis.objects.all()
        except Exception as e:
            print(f"DEBUG - Error filtering diagnoses: {e}")
            queryset = Diagnosis.objects.all()
        
        # Your existing filters
        appointment_id = self.request.query_params.get('appointment_id')
        severity = self.request.query_params.get('severity')
        follow_up_required = self.request.query_params.get('follow_up_required')
        
        if appointment_id: 
            queryset = queryset.filter(appointment_id=appointment_id)
        if severity: 
            queryset = queryset.filter(severity=severity)
        if follow_up_required: 
            queryset = queryset.filter(follow_up_required=(follow_up_required.lower() == 'true'))
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def critical_cases(self, request):
        """Get critical cases for current doctor"""
        try:
            doctors = Staff.objects.filter(role='DOCTOR')
            if doctors.exists():
                doctor_staff = doctors.first()
                critical_diagnoses = Diagnosis.objects.filter(
                    doctor=doctor_staff,
                    severity__in=['HIGH', 'CRITICAL']
                )
                serializer = self.get_serializer(critical_diagnoses, many=True)
                return Response(serializer.data)
        except Exception as e:
            print(f"DEBUG - Error in critical_cases: {e}")
        return Response([])
    
    @action(detail=False, methods=['get'])
    def follow_up_required(self, request):
        """Get follow-up required cases for current doctor"""
        try:
            doctors = Staff.objects.filter(role='DOCTOR')
            if doctors.exists():
                doctor_staff = doctors.first()
                follow_up_diagnoses = Diagnosis.objects.filter(
                    doctor=doctor_staff,
                    follow_up_required=True, 
                    follow_up_date__gte=timezone.now().date()
                )
                serializer = self.get_serializer(follow_up_diagnoses, many=True)
                return Response(serializer.data)
        except Exception as e:
            print(f"DEBUG - Error in follow_up_required: {e}")
        return Response([])

class PrescriptionViewSet(viewsets.ModelViewSet):
    queryset = Prescription.objects.all()
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter prescriptions by current doctor"""
        user = self.request.user
        
        try:
            doctors = Staff.objects.filter(role='DOCTOR')
            if doctors.exists():
                doctor_staff = doctors.first()
                queryset = Prescription.objects.filter(doctor=doctor_staff)
            else:
                queryset = Prescription.objects.all()
        except Exception as e:
            print(f"DEBUG - Error filtering prescriptions: {e}")
            queryset = Prescription.objects.all()
        
        # Your existing filters
        appointment_id = self.request.query_params.get('appointment_id')
        medicine_name = self.request.query_params.get('medicine_name')
        is_active = self.request.query_params.get('is_active')
        
        if appointment_id: 
            queryset = queryset.filter(appointment_id=appointment_id)
        if medicine_name: 
            queryset = queryset.filter(medicine_name__icontains=medicine_name)
        if is_active: 
            queryset = queryset.filter(is_active=(is_active.lower() == 'true'))
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        prescription = self.get_object()
        prescription.is_active = False
        prescription.save()
        return Response({'status': 'Prescription deactivated'})
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        prescription = self.get_object()
        prescription.is_active = True
        prescription.save()
        return Response({'status': 'Prescription activated'})
    
    @action(detail=False, methods=['get'])
    def controlled_substances(self, request):
        """Get controlled substances for current doctor"""
        try:
            doctors = Staff.objects.filter(role='DOCTOR')
            if doctors.exists():
                doctor_staff = doctors.first()
                controlled_prescriptions = Prescription.objects.filter(
                    doctor=doctor_staff,
                    is_controlled=True
                )
                serializer = self.get_serializer(controlled_prescriptions, many=True)
                return Response(serializer.data)
        except Exception as e:
            print(f"DEBUG - Error in controlled_substances: {e}")
        return Response([])

class LabRequestViewSet(viewsets.ModelViewSet):
    queryset = LabRequest.objects.all()
    serializer_class = LabRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter lab requests by current doctor"""
        user = self.request.user
        
        try:
            doctors = Staff.objects.filter(role='DOCTOR')
            if doctors.exists():
                doctor_staff = doctors.first()
                queryset = LabRequest.objects.filter(doctor=doctor_staff)
            else:
                queryset = LabRequest.objects.all()
        except Exception as e:
            print(f"DEBUG - Error filtering lab requests: {e}")
            queryset = LabRequest.objects.all()
        
        # Your existing filters
        appointment_id = self.request.query_params.get('appointment_id')
        status = self.request.query_params.get('status')
        priority = self.request.query_params.get('priority')
        
        if appointment_id: 
            queryset = queryset.filter(appointment_id=appointment_id)
        if status: 
            queryset = queryset.filter(status=status)
        if priority: 
            queryset = queryset.filter(priority=priority)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        lab_request = self.get_object()
        lab_request.mark_completed()
        return Response({'status': 'Lab request marked as completed'})
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        lab_request = self.get_object()
        if not lab_request.can_be_cancelled():
            return Response({'error': 'Cannot cancel this lab request'}, status=status.HTTP_400_BAD_REQUEST)
        lab_request.status = 'CANCELLED'
        lab_request.save()
        return Response({'status': 'Lab request cancelled'})
    
    @action(detail=False, methods=['get'])
    def urgent_requests(self, request):
        """Get urgent requests for current doctor"""
        try:
            doctors = Staff.objects.filter(role='DOCTOR')
            if doctors.exists():
                doctor_staff = doctors.first()
                urgent_requests = LabRequest.objects.filter(
                    doctor=doctor_staff,
                    priority__in=['URGENT', 'STAT'], 
                    status='REQUESTED'
                )
                serializer = self.get_serializer(urgent_requests, many=True)
                return Response(serializer.data)
        except Exception as e:
            print(f"DEBUG - Error in urgent_requests: {e}")
        return Response([])
    
    @action(detail=False, methods=['get'])
    def pending_tests(self, request):
        """Get pending tests for current doctor"""
        try:
            doctors = Staff.objects.filter(role='DOCTOR')
            if doctors.exists():
                doctor_staff = doctors.first()
                pending_tests = LabRequest.objects.filter(
                    doctor=doctor_staff,
                    status__in=['REQUESTED', 'IN_PROGRESS']
                )
                serializer = self.get_serializer(pending_tests, many=True)
                return Response(serializer.data)
        except Exception as e:
            print(f"DEBUG - Error in pending_tests: {e}")
        return Response([])