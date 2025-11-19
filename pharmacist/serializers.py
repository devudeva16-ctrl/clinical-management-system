from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import MedicineIssue, MedicineInventory

class MedicineIssueSerializer(serializers.ModelSerializer):
    patient_info = serializers.SerializerMethodField(read_only=True)
    medicine_info = serializers.SerializerMethodField(read_only=True)
    prescription_info = serializers.SerializerMethodField(read_only=True)
    needs_attention = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = MedicineIssue
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_patient_info(self, obj):
        return obj.get_patient_info()
    
    def get_medicine_info(self, obj):
        return obj.get_medicine_info()
    
    def get_prescription_info(self, obj):
        return f"{obj.prescription.medicine_name} - {obj.prescription.dosage}"
    
    def validate_pharmacist(self, value):
        if value.role != 'PHARMACIST':
            raise serializers.ValidationError('Only pharmacists can issue medicines')
        return value
    
    def validate_quantity_issued(self, value):
        if value and len(value) > 50:
            raise serializers.ValidationError('Quantity issued too long (max 50 characters)')
        return value
    
    def validate_batch_number(self, value):
        if value and len(value) < 3:
            raise serializers.ValidationError('Batch number must be at least 3 characters')
        if value and len(value) > 50:
            raise serializers.ValidationError('Batch number too long (max 50 characters)')
        return value
    
    def validate_expiry_date(self, value):
        if value and value <= timezone.now().date():
            raise serializers.ValidationError('Expiry date must be in the future')
        return value
    
    def validate_unit_price(self, value):
        if value < 0:
            raise serializers.ValidationError('Unit price cannot be negative')
        if value > 100000:
            raise serializers.ValidationError('Unit price too high')
        return value
    
    def validate_total_price(self, value):
        if value < 0:
            raise serializers.ValidationError('Total price cannot be negative')
        return value
    
    def validate_special_instructions(self, value):
        if value and len(value) > 1000:
            raise serializers.ValidationError('Special instructions too long (max 1000 characters)')
        return value
    
    def validate(self, data):
        if data.get('status') == 'ISSUED':
            if not data.get('quantity_issued'):
                raise serializers.ValidationError({'quantity_issued': 'Quantity issued is required when status is issued'})
            if not data.get('batch_number'):
                raise serializers.ValidationError({'batch_number': 'Batch number is required for issued medicines'})
            if not data.get('instructions_given', False):
                raise serializers.ValidationError({'instructions_given': 'Usage instructions must be given when issuing medicine'})
        
        if data.get('is_controlled_substance') and data.get('status') == 'ISSUED':
            if not data.get('patient_signature_obtained', False):
                raise serializers.ValidationError({'patient_signature_obtained': 'Patient signature is required for controlled substances'})
            if not data.get('controlled_substance_log'):
                raise serializers.ValidationError({'controlled_substance_log': 'Controlled substance log is required'})
        
        return data

class MedicineInventorySerializer(serializers.ModelSerializer):
    needs_restock = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = MedicineInventory
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_medicine_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError('Medicine name must be at least 2 characters')
        if len(value) > 100:
            raise serializers.ValidationError('Medicine name too long (max 100 characters)')
        return value.strip()
    
    def validate_batch_number(self, value):
        if len(value) < 3:
            raise serializers.ValidationError('Batch number must be at least 3 characters')
        if len(value) > 50:
            raise serializers.ValidationError('Batch number too long (max 50 characters)')
        return value
    
    def validate_expiry_date(self, value):
        if value <= timezone.now().date():
            raise serializers.ValidationError('Expiry date must be in the future')
        return value
    
    def validate_quantity_in_stock(self, value):
        if value < 0:
            raise serializers.ValidationError('Quantity cannot be negative')
        if value > 1000000:
            raise serializers.ValidationError('Quantity too large')
        return value
    
    def validate_reorder_level(self, value):
        if value < 0:
            raise serializers.ValidationError('Reorder level cannot be negative')
        return value
    
    def validate_unit_price(self, value):
        if value <= 0:
            raise serializers.ValidationError('Unit price must be greater than 0')
        if value > 100000:
            raise serializers.ValidationError('Unit price too high')
        return value
    
    def validate_supplier(self, value):
        if value and len(value) > 100:
            raise serializers.ValidationError('Supplier name too long (max 100 characters)')
        return value
    
    def validate_notes(self, value):
        if value and len(value) > 2000:
            raise serializers.ValidationError('Notes too long (max 2000 characters)')
        return value