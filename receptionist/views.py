from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Count, Sum
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

# Import models
from .models import Patient, Appointment
from billing.models import Billing

# Import serializers
from .serializers import (
    PatientSerializer, 
    AppointmentSerializer, 
    BillingSerializer, 
    BillingPaymentSerializer, 
    BillingDiscountSerializer
)


class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Patient.objects.all()
        name = self.request.query_params.get('name')
        phone = self.request.query_params.get('phone')
        is_active = self.request.query_params.get('is_active')
        gender = self.request.query_params.get('gender')
        
        if name: 
            queryset = queryset.filter(name__icontains=name)
        if phone: 
            queryset = queryset.filter(phone__icontains=phone)
        if is_active: 
            queryset = queryset.filter(is_active=(is_active.lower() == 'true'))
        if gender: 
            queryset = queryset.filter(gender=gender)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        patient = self.get_object()
        patient.deactivate()
        return Response({'status': 'Patient deactivated'})
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        patient = self.get_object()
        patient.activate()
        return Response({'status': 'Patient activated'})
    
    @action(detail=True, methods=['get'])
    def appointments(self, request, pk=None):
        patient = self.get_object()
        appointments = patient.appointments.all()
        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q')
        if query:
            patients = Patient.objects.filter(
                Q(name__icontains=query) | 
                Q(phone__icontains=query) |
                Q(email__icontains=query)
            )
            serializer = self.get_serializer(patients, many=True)
            return Response(serializer.data)
        return Response([])
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        total_patients = Patient.objects.count()
        active_patients = Patient.objects.filter(is_active=True).count()
        new_today = Patient.objects.filter(created_at__date=date.today()).count()
        return Response({
            'total_patients': total_patients,
            'active_patients': active_patients,
            'new_today': new_today
        })


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Appointment.objects.all()
        patient_id = self.request.query_params.get('patient_id')
        doctor_id = self.request.query_params.get('doctor_id')
        status = self.request.query_params.get('status')
        date = self.request.query_params.get('date')
        priority = self.request.query_params.get('priority')
        
        if patient_id: 
            queryset = queryset.filter(patient_id=patient_id)
        if doctor_id: 
            queryset = queryset.filter(doctor_id=doctor_id)
        if status: 
            queryset = queryset.filter(status=status)
        if date: 
            queryset = queryset.filter(appointment_date=date)
        if priority: 
            queryset = queryset.filter(priority=priority)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def mark_confirmed(self, request, pk=None):
        appointment = self.get_object()
        appointment.mark_confirmed()
        return Response({'status': 'Appointment confirmed'})
    
    @action(detail=True, methods=['post'])
    def mark_in_progress(self, request, pk=None):
        appointment = self.get_object()
        appointment.mark_in_progress()
        return Response({'status': 'Appointment marked as in progress'})
    
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        appointment = self.get_object()
        actual_duration = request.data.get('actual_duration')
        appointment.mark_completed(actual_duration)
        return Response({'status': 'Appointment completed'})
    
    @action(detail=True, methods=['post'])
    def mark_cancelled(self, request, pk=None):
        appointment = self.get_object()
        appointment.mark_cancelled()
        return Response({'status': 'Appointment cancelled'})
    
    @action(detail=False, methods=['get'])
    def todays_appointments(self, request):
        doctor_id = request.query_params.get('doctor_id')
        appointments = Appointment.get_todays_appointments(doctor_id)
        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming_appointments(self, request):
        days = int(request.query_params.get('days', 7))
        appointments = Appointment.get_upcoming_appointments(days)
        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue_appointments(self, request):
        overdue_appointments = [appt for appt in Appointment.objects.filter(status__in=['SCHEDULED', 'CONFIRMED']) if appt.is_overdue()]
        serializer = self.get_serializer(overdue_appointments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def available_slots(self, request):
        doctor_id = request.query_params.get('doctor_id')
        date_str = request.query_params.get('date')
        
        if not doctor_id or not date_str:
            return Response({'error': 'Doctor ID and date are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            slot_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
            booked_slots = Appointment.objects.filter(
                doctor_id=doctor_id,
                appointment_date=slot_date,
                status__in=['SCHEDULED', 'CONFIRMED']
            ).values_list('appointment_time', flat=True)
            
            # Generate available slots (every 30 minutes from 8 AM to 8 PM)
            available_slots = []
            start_time = timezone.datetime.strptime('08:00', '%H:%M').time()
            end_time = timezone.datetime.strptime('20:00', '%H:%M').time()
            
            current_time = start_time
            while current_time <= end_time:
                if current_time not in booked_slots:
                    available_slots.append(current_time.strftime('%H:%M'))
                # Add 30 minutes
                current_time = (timezone.datetime.combine(date.today(), current_time) + timedelta(minutes=30)).time()
            
            return Response({'available_slots': available_slots})
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)


class BillingViewSet(viewsets.ModelViewSet):
    queryset = Billing.objects.all()
    serializer_class = BillingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Billing.objects.all()
        
        # Filter by patient
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        
        # Filter by payment status
        payment_status = self.request.query_params.get('payment_status')
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(billing_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(billing_date__lte=end_date)
        
        # Filter overdue bills
        overdue = self.request.query_params.get('overdue')
        if overdue and overdue.lower() == 'true':
            today = timezone.now().date()
            queryset = queryset.filter(
                payment_status__in=['PENDING', 'PARTIAL'],
                due_date__lt=today
            )
        
        # Search by bill number or patient name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(bill_number__icontains=search) |
                Q(patient__full_name__icontains=search) |
                Q(patient__phone__icontains=search)
            )
        
        return queryset
    
    def perform_create(self, serializer):
        # Auto-set created_by to current user's staff profile
        serializer.save(created_by=self.request.user.staff_profile)
    
    @action(detail=True, methods=['post'])
    def add_payment(self, request, pk=None):
        """Add payment to a bill"""
        billing = self.get_object()
        serializer = BillingPaymentSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                billing.add_payment(
                    amount=serializer.validated_data['amount'],
                    method=serializer.validated_data['payment_method'],
                    notes=serializer.validated_data.get('notes', '')
                )
                return Response({
                    'status': 'Payment added successfully',
                    'bill': BillingSerializer(billing).data
                })
            except ValidationError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark bill as fully paid"""
        billing = self.get_object()
        payment_method = request.data.get('payment_method', 'CASH')
        notes = request.data.get('notes', '')
        
        try:
            billing.mark_as_paid(method=payment_method, notes=notes)
            return Response({
                'status': 'Bill marked as paid',
                'bill': BillingSerializer(billing).data
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def apply_discount(self, request, pk=None):
        """Apply discount to bill"""
        billing = self.get_object()
        serializer = BillingDiscountSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                billing.apply_discount(
                    discount_amount=serializer.validated_data['discount_amount'],
                    reason=serializer.validated_data.get('reason', '')
                )
                return Response({
                    'status': 'Discount applied successfully',
                    'bill': BillingSerializer(billing).data
                })
            except ValidationError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get bill summary"""
        billing = self.get_object()
        return Response(billing.get_bill_summary())
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get billing statistics"""
        total_revenue = Billing.get_total_revenue()
        pending_bills = Billing.get_pending_bills().count()
        overdue_bills = Billing.get_overdue_bills().count()
        paid_bills = Billing.objects.filter(payment_status='PAID').count()
        
        # Today's revenue
        today = timezone.now().date()
        today_revenue = Billing.get_total_revenue(start_date=today)
        
        # This month's revenue
        month_start = today.replace(day=1)
        month_revenue = Billing.get_total_revenue(start_date=month_start)
        
        return Response({
            'total_revenue': float(total_revenue),
            'today_revenue': float(today_revenue),
            'month_revenue': float(month_revenue),
            'pending_bills': pending_bills,
            'overdue_bills': overdue_bills,
            'paid_bills': paid_bills
        })
    
    @action(detail=False, methods=['get'])
    def patient_bills(self, request):
        """Get all bills for a specific patient"""
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': 'patient_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        bills = Billing.objects.filter(patient_id=patient_id)
        serializer = self.get_serializer(bills, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get all overdue bills"""
        overdue_bills = Billing.get_overdue_bills()
        serializer = self.get_serializer(overdue_bills, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending bills"""
        pending_bills = Billing.get_pending_bills()
        serializer = self.get_serializer(pending_bills, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search bills by various criteria"""
        query = request.query_params.get('q')
        if not query:
            return Response([])
        
        bills = Billing.objects.filter(
            Q(bill_number__icontains=query) |
            Q(patient__full_name__icontains=query) |
            Q(patient__phone__icontains=query) |
            Q(patient__email__icontains=query)
        )
        serializer = self.get_serializer(bills, many=True)
        return Response(serializer.data)