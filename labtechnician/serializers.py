from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import LabReport, LabEquipment

class LabReportSerializer(serializers.ModelSerializer):
    patient_info = serializers.SerializerMethodField(read_only=True)
    test_info = serializers.SerializerMethodField(read_only=True)
    doctor_info = serializers.SerializerMethodField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    turnaround_time = serializers.FloatField(read_only=True)
    can_be_verified = serializers.BooleanField(read_only=True)
    is_urgent = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = LabReport
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'critical_result_acknowledged_date']
    
    def get_patient_info(self, obj):
        return obj.get_patient_info()
    
    def get_test_info(self, obj):
        return obj.get_test_info()
    
    def get_doctor_info(self, obj):
        return obj.get_doctor_info()
    
    def validate_technician(self, value):
        if value.role != 'LABTECH':
            raise serializers.ValidationError('Only lab technicians can be assigned to lab reports')
        return value
    
    def validate_results(self, value):
        if value and len(value.strip()) < 10:
            raise serializers.ValidationError('Results must be at least 10 characters long')
        if value and len(value) > 10000:
            raise serializers.ValidationError('Results too long (max 10000 characters)')
        return value
    
    def validate_comments(self, value):
        if value and len(value) > 2000:
            raise serializers.ValidationError('Comments too long (max 2000 characters)')
        return value
    
    def validate_measured_value(self, value):
        if value is not None:
            if value < 0:
                raise serializers.ValidationError('Measured value cannot be negative')
            if value > 9999999.99:
                raise serializers.ValidationError('Measured value too large')
        return value
    
    def validate_test_date(self, value):
        if value > timezone.now():
            raise serializers.ValidationError('Test date cannot be in the future')
        return value
    
    def validate(self, data):
        if data.get('status') in ['COMPLETED', 'VERIFIED']:
            if not data.get('results') and not data.get('result_file'):
                raise serializers.ValidationError({'results': 'Results or result file is required for completed reports'})
            if not data.get('result_status'):
                raise serializers.ValidationError({'result_status': 'Result status is required for completed reports'})
        
        if data.get('measured_value') is not None:
            if data.get('normal_range_min') is None or data.get('normal_range_max') is None:
                raise serializers.ValidationError({'measured_value': 'Normal range must be specified when providing measured value'})
        
        if data.get('status') == 'VERIFIED' and not data.get('verified_by'):
            raise serializers.ValidationError({'verified_by': 'Verified by doctor is required for verified reports'})
        
        return data

class LabEquipmentSerializer(serializers.ModelSerializer):
    needs_calibration = serializers.BooleanField(read_only=True)
    needs_maintenance = serializers.BooleanField(read_only=True)
    is_operational = serializers.BooleanField(read_only=True)
    calibration_status = serializers.CharField(read_only=True)
    
    class Meta:
        model = LabEquipment
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_serial_number(self, value):
        if LabEquipment.objects.filter(serial_number=value).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError('Equipment with this serial number already exists')
        return value
    
    def validate_calibration_due_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError('Calibration due date cannot be in the past')
        return value
    
    def validate_last_calibration_date(self, value):
        if value and value > timezone.now().date():
            raise serializers.ValidationError('Last calibration date cannot be in the future')
        return value
    
    def validate_next_maintenance_date(self, value):
        if value and value < timezone.now().date():
            raise serializers.ValidationError('Next maintenance date cannot be in the past')
        return value
    
    def validate_last_maintenance_date(self, value):
        if value and value > timezone.now().date():
            raise serializers.ValidationError('Last maintenance date cannot be in the future')
        return value