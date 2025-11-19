# doctor/serializers.py
from rest_framework import serializers
from receptionist.models import Appointment, Patient
from adminapp.models import Staff
from .models import Diagnosis, Prescription, LabRequest

class PatientMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'name', 'age', 'gender', 'phone', 'blood_group']

class DoctorAppointmentSerializer(serializers.ModelSerializer):
    patient_details = PatientMiniSerializer(source='patient', read_only=True)
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True)
    is_urgent = serializers.SerializerMethodField()
    is_today = serializers.SerializerMethodField()
    can_start_consultation = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = [
            'id',
            'patient', 'patient_details', 'doctor', 'doctor_name',
            'appointment_date', 'appointment_time', 'purpose', 'status',
            'priority', 'symptoms', 'notes', 'estimated_duration',
            'actual_duration', 'check_in_time', 'check_out_time',
            'created_at', 'is_urgent', 'is_today', 'can_start_consultation'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_is_urgent(self, obj):
        return obj.priority == 'URGENT'
    
    def get_is_today(self, obj):
        from datetime import date
        return obj.appointment_date == date.today()
    
    def get_can_start_consultation(self, obj):
        return obj.status in ['SCHEDULED', 'CONFIRMED']

# Keep your existing serializers for Diagnosis, Prescription, LabRequest
class DiagnosisSerializer(serializers.ModelSerializer):
    patient_info = serializers.SerializerMethodField(read_only=True)
    condition_summary = serializers.SerializerMethodField(read_only=True)
    requires_immediate_attention = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Diagnosis
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_patient_info(self, obj):
        return obj.get_patient_info()
    
    def get_condition_summary(self, obj):
        return obj.get_condition_summary()
    
    def validate_symptoms(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError('Symptoms description must be at least 10 characters')
        if len(value.strip()) > 10000:
            raise serializers.ValidationError('Symptoms description too long (max 10000 characters)')
        return value
    
    def validate_diagnosis(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError('Diagnosis must be at least 5 characters')
        if len(value.strip().split()) < 2:
            raise serializers.ValidationError('Diagnosis should contain at least 2 words')
        if len(value) > 5000:
            raise serializers.ValidationError('Diagnosis too long (max 5000 characters)')
        return value

class PrescriptionSerializer(serializers.ModelSerializer):
    duration_display = serializers.SerializerMethodField(read_only=True)
    frequency_display_full = serializers.SerializerMethodField(read_only=True)
    is_long_term = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Prescription
        fields = '__all__'
        read_only_fields = ['created_at']
    
    def get_duration_display(self, obj):
        return obj.get_duration_display()
    
    def get_frequency_display_full(self, obj):
        return obj.get_frequency_display_full()
    
    def validate_medicine_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError('Medicine name must be at least 2 characters')
        if len(value) > 100:
            raise serializers.ValidationError('Medicine name too long (max 100 characters)')
        return value.strip()

class LabRequestSerializer(serializers.ModelSerializer):
    patient_info = serializers.SerializerMethodField(read_only=True)
    test_info = serializers.SerializerMethodField(read_only=True)
    is_urgent = serializers.BooleanField(read_only=True)
    turnaround_time = serializers.DurationField(read_only=True)
    
    class Meta:
        model = LabRequest
        fields = '__all__'
        read_only_fields = ['requested_date', 'completed_date']
    
    def get_patient_info(self, obj):
        return obj.get_patient_info()
    
    def get_test_info(self, obj):
        return obj.get_test_info()
    
    def validate_test_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError('Test name must be at least 2 characters')
        if len(value) > 100:
            raise serializers.ValidationError('Test name too long (max 100 characters)')
        return value.strip()