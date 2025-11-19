from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

class Staff(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('RECEPTIONIST', 'Receptionist'),
        ('DOCTOR', 'Doctor'),
        ('PHARMACIST', 'Pharmacist'),
        ('LABTECH', 'Lab Technician'),
    ]

    name_validator = RegexValidator(
        regex=r'^[a-zA-ZÀ-ÿ\s\'\-\.]{2,100}$',
        message='Name must contain only letters, spaces, apostrophes, hyphens and dots (2-100 characters)'
    )
    
    full_name = models.CharField(
        max_length=100,
        validators=[name_validator],
        help_text="Enter full name (2-100 characters)"
    )
    
    email = models.EmailField(
        unique=True,
        help_text="Enter a valid email address"
    )
    
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES,
        help_text="Select staff role"
    )
    
    # Password field - store hashed passwords
    password = models.CharField(
        max_length=128,
        verbose_name="Password Hash",
        help_text="Hashed password (automatically set when using set_password method)"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Is this staff member active?"
    )
    
    date_joined = models.DateTimeField(
        auto_now_add=True,
        help_text="Date when staff member joined"
    )
    
    last_login = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Last login date"
    )

    class Meta:
        verbose_name = "Staff"
        verbose_name_plural = "Staff"
        ordering = ['full_name']

    def set_password(self, raw_password):
        """Hash and set the password"""
        if not raw_password:
            raise ValidationError('Password cannot be empty')
        
        if len(raw_password) < 8:
            raise ValidationError('Password must be at least 8 characters long')
        
        if not any(char.isdigit() for char in raw_password):
            raise ValidationError('Password must contain at least one digit')
        
        if not any(char.isalpha() for char in raw_password):
            raise ValidationError('Password must contain at least one letter')
        
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """Check if the raw password matches the hashed one"""
        if not raw_password or not self.password:
            return False
        return check_password(raw_password, self.password)

    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = timezone.now()
        self.save(update_fields=['last_login'])

    def clean(self):
        """Additional model-level validation"""
        errors = {}
        
        # Email domain validation (optional - you might want to remove this)
        allowed_domains = ['hospital.com', 'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']
        if allowed_domains:
            email_domain = self.email.split('@')[-1] if '@' in self.email else ''
            if email_domain.lower() not in allowed_domains:
                errors['email'] = f'Please use an email from allowed domains: {", ".join(allowed_domains)}'
        
        # Name format validation
        if not self.full_name or len(self.full_name.strip()) == 0:
            errors['full_name'] = 'Please enter a valid name'
        else:
            name_parts = self.full_name.strip().split()
            if len(name_parts) < 1:
                errors['full_name'] = 'Please enter a valid name'
            
            # Validate name doesn't contain multiple special characters in a row
            if '  ' in self.full_name or '..' in self.full_name or '--' in self.full_name:
                errors['full_name'] = 'Name contains invalid character sequences'
        
        # Check if password is set for new instances
        if not self.pk and not self.password:  # New instance without password
            errors['password'] = 'Password is required'
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Override save to run full validation"""
        # Don't auto-hash password here to avoid double hashing
        # Password should be set using set_password method
        
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.full_name} ({self.role}) - {status}"