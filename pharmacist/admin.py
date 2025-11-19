from django.contrib import admin
from django import forms
from .models import MedicineIssue, MedicineInventory
from django.utils import timezone

class MedicineIssueAdminForm(forms.ModelForm):
    class Meta:
        model = MedicineIssue
        fields = '__all__'
    
    def clean_pharmacist(self):
        pharmacist = self.cleaned_data.get('pharmacist')
        if pharmacist and pharmacist.role != 'PHARMACIST':
            raise forms.ValidationError('Only pharmacists can issue medicines')
        return pharmacist
    
    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')
        if expiry_date and expiry_date <= timezone.now().date():
            raise forms.ValidationError('Expiry date must be in the future')
        return expiry_date

@admin.register(MedicineIssue)
class MedicineIssueAdmin(admin.ModelAdmin):
    form = MedicineIssueAdminForm
    list_display = ['prescription', 'pharmacist', 'status', 'issued', 'payment_status', 'issue_date', 'is_controlled_substance']
    list_filter = ['status', 'payment_status', 'issued', 'is_controlled_substance', 'issue_date']
    search_fields = ['prescription__medicine_name', 'prescription__appointment__patient__full_name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Prescription Info', {'fields': ('prescription', 'pharmacist')}),
        ('Issuance Details', {'fields': ('status', 'issued', 'issue_date', 'issue_time', 'quantity_issued')}),
        ('Medicine Details', {'fields': ('batch_number', 'expiry_date', 'unit_price', 'total_price')}),
        ('Patient Education', {'fields': ('instructions_given', 'special_instructions', 'side_effects_explained')}),
        ('Payment', {'fields': ('payment_status',)}),
        ('Controlled Substances', {'fields': ('is_controlled_substance', 'controlled_substance_log', 'patient_signature_obtained')}),
        ('System', {'fields': ('created_at', 'updated_at')}),
    )

class MedicineInventoryAdminForm(forms.ModelForm):
    class Meta:
        model = MedicineInventory
        fields = '__all__'
    
    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')
        if expiry_date <= timezone.now().date():
            raise forms.ValidationError('Expiry date must be in the future')
        return expiry_date
    
    def clean_quantity_in_stock(self):
        quantity = self.cleaned_data.get('quantity_in_stock')
        if quantity < 0:
            raise forms.ValidationError('Quantity cannot be negative')
        return quantity

@admin.register(MedicineInventory)
class MedicineInventoryAdmin(admin.ModelAdmin):
    form = MedicineInventoryAdminForm
    list_display = ['medicine_name', 'batch_number', 'category', 'quantity_in_stock', 'reorder_level', 'unit_price', 'expiry_date', 'needs_restock', 'is_expiring_soon']
    list_filter = ['category', 'is_controlled', 'last_restocked']
    search_fields = ['medicine_name', 'generic_name', 'batch_number']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Info', {'fields': ('medicine_name', 'generic_name', 'category', 'is_controlled')}),
        ('Batch Details', {'fields': ('batch_number', 'expiry_date', 'supplier')}),
        ('Stock Management', {'fields': ('quantity_in_stock', 'reorder_level', 'unit_price', 'last_restocked')}),
        ('Additional', {'fields': ('notes', 'created_at', 'updated_at')}),
    )
    
    def needs_restock(self, obj):
        return obj.needs_restock()
    needs_restock.boolean = True
    
    def is_expiring_soon(self, obj):
        return obj.is_expiring_soon()
    is_expiring_soon.boolean = True