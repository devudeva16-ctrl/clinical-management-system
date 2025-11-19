from django.contrib import admin
from django import forms
from .models import Patient, Appointment
from django.utils import timezone

class PatientAdminForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = '__all__'
    
    def clean_age(self):
        age = self.cleaned_data.get('age')
        if age < 1:
            raise forms.ValidationError('Age must be at least 1 year')
        if age > 120:
            raise forms.ValidationError('Please verify age (over 120 years)')
        return age
    
    def clean_address(self):
        address = self.cleaned_data.get('address')
        if len(address.strip()) < 10:
            raise forms.ValidationError('Address must be at least 10 characters')
        return address

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    form = PatientAdminForm
    list_display = ['name', 'age', 'gender', 'phone', 'is_active', 'created_at']
    list_filter = ['gender', 'is_active', 'blood_group', 'created_at']
    search_fields = ['name', 'phone', 'email']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Personal Info', {'fields': ('name', 'age', 'gender', 'blood_group')}),
        ('Contact Info', {'fields': ('address', 'phone', 'email', 'emergency_contact')}),
        ('Medical Info', {'fields': ('medical_history', 'allergies')}),
        ('System', {'fields': ('created_by', 'is_active', 'created_at', 'updated_at')}),
    )

class AppointmentAdminForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = '__all__'
    
    def clean_appointment_date(self):
        appointment_date = self.cleaned_data.get('appointment_date')
        if appointment_date < timezone.now().date():
            raise forms.ValidationError('Cannot book appointments in the past')
        return appointment_date
    
    def clean_purpose(self):
        purpose = self.cleaned_data.get('purpose')
        if len(purpose.strip()) < 5:
            raise forms.ValidationError('Please describe appointment purpose (at least 5 characters)')
        return purpose

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    form = AppointmentAdminForm
    list_display = ['patient', 'doctor', 'appointment_date', 'appointment_time', 'status', 'priority', 'created_by']
    list_filter = ['status', 'priority', 'appointment_date', 'created_at']
    search_fields = ['patient__name', 'doctor__full_name', 'purpose']
    readonly_fields = ['created_at', 'updated_at', 'check_in_time', 'check_out_time']
    fieldsets = (
        ('Appointment Details', {'fields': ('patient', 'doctor', 'appointment_date', 'appointment_time', 'purpose')}),
        ('Status & Priority', {'fields': ('status', 'priority', 'estimated_duration', 'actual_duration')}),
        ('Additional Info', {'fields': ('symptoms', 'notes')}),
        ('Check-in/out', {'fields': ('check_in_time', 'check_out_time')}),
        ('System', {'fields': ('created_by', 'created_at', 'updated_at')}),
    )