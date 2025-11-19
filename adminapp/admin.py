from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from .models import Staff

class StaffAdminForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = '__all__'
    
    def clean_full_name(self):
        name = self.cleaned_data.get('full_name')
        if not name or len(name.strip()) < 2: raise ValidationError('Name must be at least 2 characters long')
        if len(name) > 100: raise ValidationError('Name cannot exceed 100 characters')
        if '  ' in name or '..' in name or '--' in name: raise ValidationError('Name contains invalid character sequences')
        return name.strip()
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        allowed_domains = ['hospital.com', 'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']
        email_domain = email.split('@')[-1].lower() if '@' in email else ''
        if email_domain not in allowed_domains: raise ValidationError(f'Email domain must be one of: {", ".join(allowed_domains)}')
        return email.lower()

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    form = StaffAdminForm
    list_display = ['full_name', 'email', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'date_joined']
    search_fields = ['full_name', 'email']
    readonly_fields = ['date_joined', 'last_login']
    fieldsets = (
        (None, {'fields': ('full_name', 'email', 'role', 'is_active')}),
        ('Authentication', {'fields': ('password',)}),
        ('Timestamps', {'fields': ('date_joined', 'last_login')}),
    )