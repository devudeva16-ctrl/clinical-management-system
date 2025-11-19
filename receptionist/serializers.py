from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, datetime
from .models import Patient, Appointment
from billing.models import Billing  # Import from billing app

class PatientSerializer(serializers.ModelSerializer):
    appointment_count = serializers.IntegerField(read_only=True)
    has_allergies = serializers.BooleanField(read_only=True)
    has_medical_history = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Patient
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError('Name must be at least 2 characters')
        if len(value) > 100:
            raise serializers.ValidationError('Name too long (max 100 characters)')
        return value.strip()
    
    def validate_age(self, value):
        if value < 1:
            raise serializers.ValidationError('Age must be at least 1 year')
        if value > 120:
            raise serializers.ValidationError('Please verify age (over 120 years)')
        return value
    
    def validate_address(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError('Address must be at least 10 characters')
        if len(value) > 500:
            raise serializers.ValidationError('Address too long (max 500 characters)')
        return value
    
    def validate_phone(self, value):
        if len(value) < 9 or len(value) > 15:
            raise serializers.ValidationError('Phone number must be 9-15 digits')
        return value
    
    def validate_emergency_contact(self, value):
        if value and (len(value) < 9 or len(value) > 15):
            raise serializers.ValidationError('Emergency contact must be 9-15 digits')
        return value
    
    def validate_medical_history(self, value):
        if value and len(value) > 2000:
            raise serializers.ValidationError('Medical history too long (max 2000 characters)')
        return value
    
    def validate_allergies(self, value):
        if value and len(value) > 1000:
            raise serializers.ValidationError('Allergies description too long (max 1000 characters)')
        return value
    
    def validate(self, data):
        if data.get('emergency_contact') and data.get('phone') == data.get('emergency_contact'):
            raise serializers.ValidationError({'emergency_contact': 'Emergency contact cannot be the same as patient phone'})
        return data

class AppointmentSerializer(serializers.ModelSerializer):
    patient_info = serializers.SerializerMethodField(read_only=True)
    doctor_info = serializers.SerializerMethodField(read_only=True)
    is_urgent = serializers.BooleanField(read_only=True)
    can_be_cancelled = serializers.BooleanField(read_only=True)
    is_future_appointment = serializers.BooleanField(read_only=True)
    is_today = serializers.BooleanField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Appointment
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'check_in_time', 'check_out_time']
    
    def get_patient_info(self, obj):
        return obj.get_patient_info()
    
    def get_doctor_info(self, obj):
        return obj.get_doctor_info()
    
    def validate_appointment_date(self, value):
        if value < date.today():
            raise serializers.ValidationError('Cannot book appointments in the past')
        
        max_future_date = date.today() + timezone.timedelta(days=180)
        if value > max_future_date:
            raise serializers.ValidationError('Cannot book appointments more than 6 months in advance')
        return value
    
    def validate_appointment_time(self, value):
        start_time = timezone.datetime.strptime('08:00', '%H:%M').time()
        end_time = timezone.datetime.strptime('20:00', '%H:%M').time()
        
        if not (start_time <= value <= end_time):
            raise serializers.ValidationError('Appointments can only be scheduled between 8:00 AM and 8:00 PM')
        return value
    
    def validate_purpose(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError('Please describe appointment purpose (at least 5 characters)')
        if len(value) > 1000:
            raise serializers.ValidationError('Purpose too long (max 1000 characters)')
        return value
    
    def validate_symptoms(self, value):
        if value and len(value) > 2000:
            raise serializers.ValidationError('Symptoms description too long (max 2000 characters)')
        return value
    
    def validate_notes(self, value):
        if value and len(value) > 1000:
            raise serializers.ValidationError('Notes too long (max 1000 characters)')
        return value
    
    def validate_estimated_duration(self, value):
        if value < 5 or value > 180:
            raise serializers.ValidationError('Estimated duration must be between 5 and 180 minutes')
        return value
    
    def validate_actual_duration(self, value):
        if value and value < 1:
            raise serializers.ValidationError('Actual duration must be at least 1 minute')
        return value
    
    def validate(self, data):
        if data.get('status') == 'COMPLETED' and not data.get('actual_duration'):
            raise serializers.ValidationError({'actual_duration': 'Actual duration is required for completed appointments'})
        return data

class BillingSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_phone = serializers.CharField(source='patient.phone', read_only=True)
    prescription_details = serializers.CharField(source='prescription.notes', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Billing
        fields = '__all__'
        read_only_fields = ['bill_number', 'created_at', 'updated_at', 'total_amount', 'balance_due']
    
    def validate_consultation_fee(self, value):
        if value < 0:
            raise serializers.ValidationError('Consultation fee cannot be negative')
        if value > 100000:
            raise serializers.ValidationError('Consultation fee too high')
        return value
    
    def validate_medicine_cost(self, value):
        if value < 0:
            raise serializers.ValidationError('Medicine cost cannot be negative')
        if value > 1000000:
            raise serializers.ValidationError('Medicine cost too high')
        return value
    
    def validate_lab_cost(self, value):
        if value < 0:
            raise serializers.ValidationError('Lab cost cannot be negative')
        if value > 1000000:
            raise serializers.ValidationError('Lab cost too high')
        return value
    
    def validate_other_charges(self, value):
        if value < 0:
            raise serializers.ValidationError('Other charges cannot be negative')
        if value > 100000:
            raise serializers.ValidationError('Other charges too high')
        return value
    
    def validate_discount(self, value):
        if value < 0:
            raise serializers.ValidationError('Discount cannot be negative')
        return value
    
    def validate_tax_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('Tax amount cannot be negative')
        if value > 100000:
            raise serializers.ValidationError('Tax amount too high')
        return value
    
    def validate_amount_paid(self, value):
        if value < 0:
            raise serializers.ValidationError('Amount paid cannot be negative')
        return value
    
    def validate_due_date(self, value):
        if value and value < timezone.now().date():
            raise serializers.ValidationError('Due date cannot be in the past')
        return value
    
    def validate(self, data):
        # Validate that amount paid doesn't exceed total amount
        if 'amount_paid' in data and 'total_amount' in data:
            if data['amount_paid'] > data.get('total_amount', 0):
                raise serializers.ValidationError({
                    'amount_paid': 'Amount paid cannot exceed total amount'
                })
        
        return data

class BillingPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    payment_method = serializers.ChoiceField(choices=Billing.PAYMENT_METHOD_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)

class BillingDiscountSerializer(serializers.Serializer):
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    reason = serializers.CharField(required=False, allow_blank=True)