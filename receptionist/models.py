from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, time, datetime


class Patient(models.Model):
    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
    ]

    # Name validation
    name_validator = RegexValidator(
        regex=r'^[a-zA-ZÀ-ÿ\s\'\-\.]{2,100}$',  # Expanded to include accented chars, apostrophes, hyphens
        message='Name must contain only letters, spaces, apostrophes, hyphens and dots (2-100 characters)'
    )
    
    # Age validation
    age_validator = [
        MinValueValidator(0, message='Age cannot be negative'),
        MaxValueValidator(150, message='Age cannot exceed 150 years')
    ]
    
    # Phone validation
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message='Phone number must be 9-15 digits, optionally starting with +'
    )

    name = models.CharField(
        max_length=100,
        validators=[name_validator],
        help_text="Enter patient's full name"
    )
    
    age = models.IntegerField(
        validators=age_validator,
        help_text="Patient age"
    )
    
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        help_text="Select patient's gender"
    )
    
    address = models.TextField(
        validators=[MinLengthValidator(10, message='Address must be at least 10 characters long')],
        help_text="Enter complete address"
    )
    
    phone = models.CharField(
        max_length=15,
        validators=[phone_validator],
        unique=True,
        help_text="Enter phone number"
    )
    
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Patient email address (optional)"
    )
    
    emergency_contact = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        validators=[phone_validator],
        help_text="Emergency contact number"
    )
    
    blood_group = models.CharField(
        max_length=5,
        blank=True,
        null=True,
        choices=[
            ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'),
            ('O+', 'O+'), ('O-', 'O-'), ('AB+', 'AB+'), ('AB-', 'AB-')
        ],
        help_text="Patient blood group"
    )
    
    # System fields
    created_by = models.ForeignKey(
        'adminapp.Staff',  # Use string reference
        on_delete=models.SET_NULL, 
        null=True,
        limit_choices_to={'role': 'RECEPTIONIST'},
        help_text="Receptionist who registered the patient"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    
    medical_history = models.TextField(
        blank=True,
        null=True,
        help_text="Any known medical conditions or history"
    )
    
    allergies = models.TextField(
        blank=True,
        null=True,
        help_text="Any known allergies"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Is this patient active in the system?"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Patient"
        verbose_name_plural = "Patients"
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]

    def clean(self):
        """Patient validation"""
        errors = {}
        
        # Age validation
        if self.age < 1:
            errors['age'] = 'Age must be at least 1 year'
        elif self.age > 120:
            errors['age'] = 'Please verify age (over 120 years)'
        
        # Phone uniqueness is handled by unique constraint, but we can add custom message
        if Patient.objects.filter(phone=self.phone).exclude(pk=self.pk).exists():
            errors['phone'] = 'This phone number is already registered'
        
        # Validate created_by role
        if self.created_by and self.created_by.role != 'RECEPTIONIST':
            errors['created_by'] = 'Only receptionist staff can register patients'
        
        # Validate email format if provided
        if self.email:
            from django.core.validators import validate_email
            try:
                validate_email(self.email)
            except ValidationError:
                errors['email'] = 'Enter a valid email address'
        
        # Validate emergency contact if provided
        if self.emergency_contact and self.emergency_contact == self.phone:
            errors['emergency_contact'] = 'Emergency contact cannot be the same as patient phone'
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Override save to run validation and formatting"""
        self.full_clean()
        
        # Capitalize name
        if self.name:
            self.name = ' '.join(word.capitalize() for word in self.name.split())
        
        super().save(*args, **kwargs)

    def get_appointment_count(self):
        """Get total appointments for this patient"""
        return self.appointments.count()

    def get_recent_appointments(self, limit=5):
        """Get recent appointments"""
        return self.appointments.all().order_by('-appointment_date', '-appointment_time')[:limit]

    def get_active_appointments(self):
        """Get active (scheduled/confirmed) appointments"""
        return self.appointments.filter(status__in=['SCHEDULED', 'CONFIRMED'])

    def deactivate(self):
        """Deactivate patient"""
        self.is_active = False
        self.save()

    def activate(self):
        """Activate patient"""
        self.is_active = True
        self.save()

    @property
    def has_allergies(self):
        """Check if patient has allergies"""
        return bool(self.allergies and self.allergies.strip())

    @property
    def has_medical_history(self):
        """Check if patient has medical history"""
        return bool(self.medical_history and self.medical_history.strip())

    def __str__(self):
        return f"{self.name} ({self.age} years)"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('CONFIRMED', 'Confirmed'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('NO_SHOW', 'No Show'),
    ]
    
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'), 
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]

    patient = models.ForeignKey(
        Patient, 
        on_delete=models.CASCADE,
        related_name='appointments',
        help_text="Select patient for appointment"
    )
    
    doctor = models.ForeignKey(
        'adminapp.Staff',  # Use string reference
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'DOCTOR'},
        help_text="Select doctor for appointment"
    )
    
    appointment_date = models.DateField(
        help_text="Select appointment date"
    )
    
    appointment_time = models.TimeField(
        help_text="Select appointment time"
    )
    
    purpose = models.TextField(
        validators=[MinLengthValidator(5, message='Please describe appointment purpose')],
        help_text="Reason for appointment"
    )
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default="SCHEDULED",
        help_text="Current appointment status"
    )
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='MEDIUM',
        help_text="Appointment priority level"
    )
    
    # Additional appointment details
    symptoms = models.TextField(
        blank=True,
        null=True,
        help_text="Initial symptoms described by patient"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about the appointment"
    )
    
    # System fields
    created_by = models.ForeignKey(
        'adminapp.Staff',  # Use string reference
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_appointments',
        limit_choices_to={'role': 'RECEPTIONIST'},
        help_text="Receptionist who created the appointment"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    
    # Additional useful fields
    estimated_duration = models.IntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(180)],
        help_text="Estimated duration in minutes"
    )
    
    actual_duration = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1)],
        help_text="Actual duration in minutes (filled after completion)"
    )
    
    check_in_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When patient checked in"
    )
    
    check_out_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When patient checked out"
    )

    class Meta:
        ordering = ['appointment_date', 'appointment_time']  # Fixed ordering to show soonest first
        verbose_name = "Appointment"
        verbose_name_plural = "Appointments"
        indexes = [
            models.Index(fields=['appointment_date', 'appointment_time']),
            models.Index(fields=['status']),
            models.Index(fields=['patient', 'doctor']),
            models.Index(fields=['priority']),
        ]
        unique_together = ['doctor', 'appointment_date', 'appointment_time']

    def clean(self):
        """Appointment validation"""
        errors = {}
        
        # Date validation
        if self.appointment_date:
            today = date.today()
            
            # Cannot book in the past
            if self.appointment_date < today:
                errors['appointment_date'] = 'Cannot book appointments in the past'
            
            # Cannot book too far in the future (6 months limit)
            from dateutil.relativedelta import relativedelta
            max_future_date = today + relativedelta(months=+6)
            if self.appointment_date > max_future_date:
                errors['appointment_date'] = 'Cannot book appointments more than 6 months in advance'
        
        # Time validation
        if self.appointment_time:
            # Clinic hours: 8 AM to 8 PM
            start_time = time(8, 0)  # 8:00 AM
            end_time = time(20, 0)   # 8:00 PM
            
            if not (start_time <= self.appointment_time <= end_time):
                errors['appointment_time'] = 'Appointments can only be scheduled between 8:00 AM and 8:00 PM'
        
        # Doctor availability validation
        if self.doctor and self.appointment_date and self.appointment_time:
            conflicting_appointments = Appointment.objects.filter(
                doctor=self.doctor,
                appointment_date=self.appointment_date,
                appointment_time=self.appointment_time,
                status__in=['SCHEDULED', 'CONFIRMED', 'IN_PROGRESS']
            ).exclude(pk=self.pk)
            
            if conflicting_appointments.exists():
                errors['__all__'] = f'Doctor {self.doctor.full_name} already has an appointment at this time'
        
        # Validate created_by role
        if self.created_by and self.created_by.role != 'RECEPTIONIST':
            errors['created_by'] = 'Only receptionist staff can create appointments'
        
        # Patient appointment limit (max 3 appointments per day)
        if self.patient and self.appointment_date:
            daily_appointments = Appointment.objects.filter(
                patient=self.patient,
                appointment_date=self.appointment_date
            ).exclude(pk=self.pk)
            
            if daily_appointments.count() >= 3:
                errors['patient'] = 'Patient cannot have more than 3 appointments per day'
        
        # Validate patient is active
        if self.patient and not self.patient.is_active:
            errors['patient'] = 'Cannot schedule appointment for inactive patient'
        
        # Validate estimated duration
        if self.estimated_duration and (self.estimated_duration < 5 or self.estimated_duration > 180):
            errors['estimated_duration'] = 'Estimated duration must be between 5 and 180 minutes'
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Override save to run validation and auto-set fields"""
        self.full_clean()
        
        # Auto-set estimated duration based on priority if not set
        if not self.estimated_duration:
            duration_map = {
                'LOW': 15,
                'MEDIUM': 30,
                'HIGH': 45,
                'URGENT': 60
            }
            self.estimated_duration = duration_map.get(self.priority, 30)
        
        super().save(*args, **kwargs)

    def get_patient_info(self):
        """Get formatted patient information"""
        return f"{self.patient.name} ({self.patient.age} years, {self.patient.get_gender_display()})"

    def get_doctor_info(self):
        """Get formatted doctor information"""
        return f"Dr. {self.doctor.full_name}"

    def is_urgent(self):
        """Check if appointment is urgent"""
        return self.priority == 'URGENT'

    def can_be_cancelled(self):
        """Check if appointment can be cancelled"""
        return self.status in ['SCHEDULED', 'CONFIRMED']

    def mark_completed(self, actual_duration=None):
        """Mark appointment as completed"""
        if self.status != 'COMPLETED':
            self.status = 'COMPLETED'
            if actual_duration:
                self.actual_duration = actual_duration
            self.check_out_time = timezone.now()
            self.save()

    def mark_in_progress(self):
        """Mark appointment as in progress"""
        if self.status in ['SCHEDULED', 'CONFIRMED']:
            self.status = 'IN_PROGRESS'
            self.check_in_time = timezone.now()
            self.save()

    def mark_confirmed(self):
        """Mark appointment as confirmed"""
        if self.status == 'SCHEDULED':
            self.status = 'CONFIRMED'
            self.save()

    def mark_cancelled(self):
        """Mark appointment as cancelled"""
        if self.can_be_cancelled():
            self.status = 'CANCELLED'
            self.save()

    def is_future_appointment(self):
        """Check if appointment is in the future"""
        today = date.today()
        now = datetime.now().time()
        
        if self.appointment_date > today:
            return True
        elif self.appointment_date == today and self.appointment_time > now:
            return True
        return False

    def is_today(self):
        """Check if appointment is today"""
        return self.appointment_date == date.today()

    def is_overdue(self):
        """Check if appointment is overdue (past scheduled time but not completed)"""
        if self.status in ['SCHEDULED', 'CONFIRMED'] and not self.is_future_appointment():
            return True
        return False

    def get_time_until_appointment(self):
        """Get time until appointment in minutes"""
        if self.is_future_appointment():
            appointment_datetime = datetime.combine(self.appointment_date, self.appointment_time)
            now = timezone.now()
            time_diff = appointment_datetime - now
            return time_diff.total_seconds() / 60
        return None

    @classmethod
    def get_todays_appointments(cls, doctor=None):
        """Get today's appointments, optionally filtered by doctor"""
        queryset = cls.objects.filter(appointment_date=date.today())
        if doctor:
            queryset = queryset.filter(doctor=doctor)
        return queryset.order_by('appointment_time')

    @classmethod
    def get_upcoming_appointments(cls, days=7):
        """Get upcoming appointments in the next days"""
        from datetime import timedelta
        start_date = date.today()
        end_date = start_date + timedelta(days=days)
        return cls.objects.filter(
            appointment_date__range=[start_date, end_date],
            status__in=['SCHEDULED', 'CONFIRMED']
        ).order_by('appointment_date', 'appointment_time')

    def __str__(self):
        return f"{self.patient.name} with Dr. {self.doctor.full_name} on {self.appointment_date} at {self.appointment_time}"