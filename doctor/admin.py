from django.contrib import admin
from django import forms
from .models import Diagnosis, Prescription, LabRequest

class DiagnosisAdminForm(forms.ModelForm):
    class Meta:
        model = Diagnosis
        fields = '__all__'
    
    def clean_symptoms(self):
        symptoms = self.cleaned_data.get('symptoms')
        if len(symptoms.strip()) < 10:
            raise forms.ValidationError('Symptoms description must be at least 10 characters')
        return symptoms
    
    def clean_diagnosis(self):
        diagnosis = self.cleaned_data.get('diagnosis')
        if len(diagnosis.strip()) < 5:
            raise forms.ValidationError('Diagnosis must be at least 5 characters')
        return diagnosis

@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    form = DiagnosisAdminForm
    list_display = ['appointment', 'doctor', 'severity', 'follow_up_required', 'created_at']
    list_filter = ['severity', 'follow_up_required', 'is_chronic', 'created_at']
    search_fields = ['appointment__patient__full_name', 'symptoms', 'diagnosis']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Appointment Info', {'fields': ('appointment', 'doctor')}),
        ('Medical Details', {'fields': ('symptoms', 'diagnosis', 'severity', 'notes')}),
        ('Follow-up', {'fields': ('follow_up_required', 'follow_up_date', 'is_chronic')}),
        ('System', {'fields': ('created_at', 'updated_at')}),
    )

class PrescriptionAdminForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = '__all__'
    
    def clean_medicine_name(self):
        name = self.cleaned_data.get('medicine_name')
        if len(name.strip()) < 2:
            raise forms.ValidationError('Medicine name must be at least 2 characters')
        return name
    
    def clean_duration(self):
        duration = self.cleaned_data.get('duration')
        if duration < 1 or duration > 365:
            raise forms.ValidationError('Duration must be between 1 and 365')
        return duration

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    form = PrescriptionAdminForm
    list_display = ['medicine_name', 'appointment', 'doctor', 'dosage', 'frequency', 'is_active']
    list_filter = ['frequency', 'is_active', 'is_controlled', 'created_at']
    search_fields = ['medicine_name', 'appointment__patient__full_name']
    readonly_fields = ['created_at']
    fieldsets = (
        ('Appointment Info', {'fields': ('appointment', 'doctor')}),
        ('Medication Details', {'fields': ('medicine_name', 'dosage', 'frequency', 'duration', 'duration_unit')}),
        ('Additional Info', {'fields': ('quantity', 'instructions', 'is_active', 'is_controlled')}),
        ('System', {'fields': ('created_at',)}),
    )

class LabRequestAdminForm(forms.ModelForm):
    class Meta:
        model = LabRequest
        fields = '__all__'
    
    def clean_test_name(self):
        name = self.cleaned_data.get('test_name')
        if len(name.strip()) < 2:
            raise forms.ValidationError('Test name must be at least 2 characters')
        return name
    
    def clean_estimated_duration(self):
        duration = self.cleaned_data.get('estimated_duration')
        if duration < 1 or duration > 1440:
            raise forms.ValidationError('Estimated duration must be between 1 and 1440 minutes')
        return duration

@admin.register(LabRequest)
class LabRequestAdmin(admin.ModelAdmin):
    form = LabRequestAdminForm
    list_display = ['test_name', 'appointment', 'doctor', 'test_type', 'status', 'priority', 'requested_date']
    list_filter = ['test_type', 'status', 'priority', 'is_fasting_required', 'requested_date']
    search_fields = ['test_name', 'appointment__patient__full_name']
    readonly_fields = ['requested_date', 'completed_date']
    fieldsets = (
        ('Appointment Info', {'fields': ('appointment', 'doctor')}),
        ('Test Details', {'fields': ('test_name', 'test_type', 'test_description', 'specimen_type')}),
        ('Status & Priority', {'fields': ('status', 'priority', 'estimated_duration')}),
        ('Instructions', {'fields': ('special_instructions', 'is_fasting_required')}),
        ('Dates', {'fields': ('requested_date', 'completed_date')}),
    )