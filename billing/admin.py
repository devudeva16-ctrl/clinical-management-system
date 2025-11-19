from django.contrib import admin
from django import forms
from .models import Billing

class BillingAdminForm(forms.ModelForm):
    class Meta:
        model = Billing
        fields = '__all__'
    
    def clean_consultation_fee(self):
        fee = self.cleaned_data.get('consultation_fee')
        if fee < 0: raise forms.ValidationError('Consultation fee cannot be negative')
        return fee
    
    def clean_medicine_cost(self):
        cost = self.cleaned_data.get('medicine_cost')
        if cost < 0: raise forms.ValidationError('Medicine cost cannot be negative')
        return cost
    
    def clean_lab_cost(self):
        cost = self.cleaned_data.get('lab_cost')
        if cost < 0: raise forms.ValidationError('Lab cost cannot be negative')
        return cost
    
    def clean_other_charges(self):
        charges = self.cleaned_data.get('other_charges')
        if charges < 0: raise forms.ValidationError('Other charges cannot be negative')
        return charges

@admin.register(Billing)
class BillingAdmin(admin.ModelAdmin):
    form = BillingAdminForm
    list_display = ['bill_number', 'patient', 'total_amount', 'amount_paid', 'balance_due', 'payment_status', 'billing_date', 'is_overdue']
    list_filter = ['payment_status', 'payment_method', 'billing_date', 'due_date']
    search_fields = ['bill_number', 'patient__full_name', 'patient__phone']
    readonly_fields = ['bill_number', 'total_amount', 'balance_due', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Info', {'fields': ('bill_number', 'patient', 'prescription', 'lab_requests', 'created_by')}),
        ('Charges', {'fields': ('consultation_fee', 'medicine_cost', 'lab_cost', 'other_charges')}),
        ('Adjustments', {'fields': ('discount', 'tax_amount')}),
        ('Payment', {'fields': ('total_amount', 'amount_paid', 'balance_due', 'payment_status', 'payment_method')}),
        ('Dates', {'fields': ('billing_date', 'due_date', 'payment_date')}),
        ('Additional', {'fields': ('notes', 'created_at', 'updated_at')}),
    )
    
    def is_overdue(self, obj):
        return obj.is_overdue
    is_overdue.boolean = True