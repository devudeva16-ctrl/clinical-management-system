from rest_framework import serializers
from django.core.exceptions import ValidationError
from .models import Billing

class BillingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Billing
        fields = '__all__'
        read_only_fields = ['bill_number', 'total_amount', 'balance_due', 'created_at', 'updated_at']
    
    def validate_consultation_fee(self, value):
        if value < 0: raise serializers.ValidationError('Consultation fee cannot be negative')
        if value > 100000: raise serializers.ValidationError('Consultation fee cannot exceed 100,000')
        return value
    
    def validate_medicine_cost(self, value):
        if value < 0: raise serializers.ValidationError('Medicine cost cannot be negative')
        if value > 500000: raise serializers.ValidationError('Medicine cost cannot exceed 500,000')
        return value
    
    def validate_lab_cost(self, value):
        if value < 0: raise serializers.ValidationError('Lab cost cannot be negative')
        if value > 200000: raise serializers.ValidationError('Lab cost cannot exceed 200,000')
        return value
    
    def validate_other_charges(self, value):
        if value < 0: raise serializers.ValidationError('Other charges cannot be negative')
        if value > 100000: raise serializers.ValidationError('Other charges cannot exceed 100,000')
        return value
    
    def validate_discount(self, value):
        if value < 0: raise serializers.ValidationError('Discount cannot be negative')
        return value
    
    def validate_tax_amount(self, value):
        if value < 0: raise serializers.ValidationError('Tax amount cannot be negative')
        if value > 50000: raise serializers.ValidationError('Tax amount cannot exceed 50,000')
        return value
    
    def validate_amount_paid(self, value):
        if value < 0: raise serializers.ValidationError('Amount paid cannot be negative')
        return value
    
    def validate(self, data):
        if data.get('amount_paid', 0) > data.get('total_amount', 0):
            raise serializers.ValidationError({'amount_paid': 'Amount paid cannot exceed total amount'})
        if data.get('due_date') and data.get('billing_date') and data['due_date'] < data['billing_date']:
            raise serializers.ValidationError({'due_date': 'Due date cannot be before billing date'})
        return data
    
    def create(self, validated_data):
        billing = Billing(**validated_data)
        billing.calculate_total()
        billing.save()
        return billing
    
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.calculate_total()
        instance.save()
        return instance