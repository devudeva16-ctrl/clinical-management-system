from rest_framework import serializers
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from .models import Staff

class StaffSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    email = serializers.EmailField(validators=[EmailValidator(message="Enter a valid email address")])
    
    class Meta:
        model = Staff
        fields = ['id', 'full_name', 'email', 'role', 'password', 'is_active', 'date_joined', 'last_login']
        read_only_fields = ['date_joined', 'last_login']
    
    def validate_full_name(self, value):
        if not value or len(value.strip()) == 0: raise serializers.ValidationError('Name cannot be empty')
        name_validator = RegexValidator(regex=r'^[a-zA-ZÀ-ÿ\s\'\-\.]{2,100}$', message='Name must contain only letters, spaces, apostrophes, hyphens and dots (2-100 characters)')
        try: name_validator(value)
        except ValidationError as e: raise serializers.ValidationError(e.message)
        if '  ' in value or '..' in value or '--' in value: raise serializers.ValidationError('Name contains invalid character sequences')
        if len(value.strip()) < 2: raise serializers.ValidationError('Name must be at least 2 characters long')
        if len(value) > 100: raise serializers.ValidationError('Name cannot exceed 100 characters')
        return value.strip()
    
    def validate_email(self, value):
        if not value: raise serializers.ValidationError('Email cannot be empty')
        allowed_domains = ['hospital.com', 'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']
        email_domain = value.split('@')[-1].lower() if '@' in value else ''
        if email_domain not in allowed_domains: raise serializers.ValidationError(f'Email domain must be one of: {", ".join(allowed_domains)}')
        if Staff.objects.filter(email=value).exclude(pk=self.instance.pk if self.instance else None).exists(): raise serializers.ValidationError('Email already exists')
        return value.lower()
    
    def validate_password(self, value):
        if not value: raise serializers.ValidationError('Password cannot be empty')
        if len(value) < 8: raise serializers.ValidationError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in value): raise serializers.ValidationError('Password must contain at least one digit')
        if not any(char.isalpha() for char in value): raise serializers.ValidationError('Password must contain at least one letter')
        if not any(char.isupper() for char in value): raise serializers.ValidationError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in value): raise serializers.ValidationError('Password must contain at least one lowercase letter')
        if ' ' in value: raise serializers.ValidationError('Password cannot contain spaces')
        return value
    
    def validate_role(self, value):
        valid_roles = [choice[0] for choice in Staff.ROLE_CHOICES]
        if value not in valid_roles: raise serializers.ValidationError(f'Role must be one of: {", ".join(valid_roles)}')
        return value
    
    def validate(self, data):
        if not data.get('full_name'): raise serializers.ValidationError({'full_name': 'Full name is required'})
        if not data.get('email'): raise serializers.ValidationError({'email': 'Email is required'})
        if not data.get('role'): raise serializers.ValidationError({'role': 'Role is required'})
        if self.instance is None and not data.get('password'): raise serializers.ValidationError({'password': 'Password is required for new staff'})
        return data
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        staff = Staff(**validated_data)
        staff.set_password(password)
        staff.save()
        return staff
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items(): setattr(instance, attr, value)
        if password: instance.set_password(password)
        instance.save()
        return instance