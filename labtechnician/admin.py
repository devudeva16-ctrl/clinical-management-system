from django.contrib import admin
from django import forms
from .models import LabReport, LabEquipment

class LabReportAdminForm(forms.ModelForm):
    class Meta:
        model = LabReport
        fields = '__all__'
    
    def clean_technician(self):
        technician = self.cleaned_data.get('technician')
        if technician and technician.role != 'LABTECH':
            raise forms.ValidationError('Only lab technicians can be assigned to lab reports')
        return technician
    
    def clean_results(self):
        results = self.cleaned_data.get('results')
        if results and len(results.strip()) < 10:
            raise forms.ValidationError('Results must be at least 10 characters long')
        return results

@admin.register(LabReport)
class LabReportAdmin(admin.ModelAdmin):
    form = LabReportAdminForm
    list_display = ['lab_request', 'technician', 'status', 'result_status', 'priority', 'test_date', 'is_critical_result']
    list_filter = ['status', 'result_status', 'priority', 'is_critical_result', 'test_date']
    search_fields = ['lab_request__test_name', 'lab_request__appointment__patient__full_name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Request Info', {'fields': ('lab_request', 'technician', 'priority')}),
        ('Test Details', {'fields': ('test_date', 'completed_date', 'instrument_used')}),
        ('Results', {'fields': ('result_file', 'results', 'comments', 'result_status')}),
        ('Quantitative Results', {'fields': ('normal_range_min', 'normal_range_max', 'measured_value', 'unit')}),
        ('Quality Control', {'fields': ('is_quality_controlled', 'quality_control_notes')}),
        ('Verification', {'fields': ('status', 'verified_by', 'verification_date', 'verification_notes')}),
        ('Critical Results', {'fields': ('is_critical_result', 'critical_result_acknowledged', 'critical_result_acknowledged_by', 'critical_result_acknowledged_date')}),
        ('System', {'fields': ('created_at', 'updated_at')}),
    )

class LabEquipmentAdminForm(forms.ModelForm):
    class Meta:
        model = LabEquipment
        fields = '__all__'
    
    def clean_serial_number(self):
        serial_number = self.cleaned_data.get('serial_number')
        if LabEquipment.objects.filter(serial_number=serial_number).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Equipment with this serial number already exists')
        return serial_number

@admin.register(LabEquipment)
class LabEquipmentAdmin(admin.ModelAdmin):
    form = LabEquipmentAdminForm
    list_display = ['name', 'model', 'serial_number', 'status', 'calibration_due_date', 'needs_calibration', 'needs_maintenance']
    list_filter = ['status', 'calibration_frequency', 'is_critical_equipment']
    search_fields = ['name', 'model', 'serial_number', 'manufacturer']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'model', 'serial_number', 'manufacturer', 'location')}),
        ('Status', {'fields': ('status', 'is_critical_equipment')}),
        ('Calibration', {'fields': ('calibration_frequency', 'calibration_due_date', 'last_calibration_date')}),
        ('Maintenance', {'fields': ('last_maintenance_date', 'next_maintenance_date')}),
        ('Additional', {'fields': ('notes', 'created_at', 'updated_at')}),
    )
    
    def needs_calibration(self, obj):
        return obj.needs_calibration()
    needs_calibration.boolean = True
    
    def needs_maintenance(self, obj):
        return obj.needs_maintenance()
    needs_maintenance.boolean = True