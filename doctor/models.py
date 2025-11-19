from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

class Diagnosis(models.Model):
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    appointment = models.OneToOneField(
        'receptionist.Appointment',  # Use string reference
        on_delete=models.CASCADE,
        help_text="Select appointment for diagnosis"
    )
    
    doctor = models.ForeignKey(
        'adminapp.Staff',  # Use string reference
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'DOCTOR'},
        help_text="Diagnosing doctor"
    )
    
    symptoms = models.TextField(
        validators=[MinLengthValidator(10, message='Symptoms description must be at least 10 characters')],
        help_text="Describe patient symptoms in detail"
    )
    
    diagnosis = models.TextField(
        validators=[MinLengthValidator(5, message='Diagnosis must be at least 5 characters')],
        help_text="Enter medical diagnosis"
    )
    
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_CHOICES,
        default='MEDIUM',
        help_text="Condition severity level"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional medical notes"
    )
    
    # System fields
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    
    follow_up_required = models.BooleanField(
        default=False,
        help_text="Does the patient require follow-up?"
    )
    
    follow_up_date = models.DateField(
        blank=True,
        null=True,
        help_text="Suggested follow-up date"
    )
    
    is_chronic = models.BooleanField(
        default=False,
        help_text="Is this a chronic condition?"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Diagnosis"
        verbose_name_plural = "Diagnoses"
        indexes = [
            models.Index(fields=['appointment']),
            models.Index(fields=['doctor']),
            models.Index(fields=['severity']),
        ]

    def clean(self):
        """Diagnosis validation"""
        errors = {}
        
        # Validate appointment exists and has status
        if self.appointment:
            if not hasattr(self.appointment, 'status'):
                errors['appointment'] = 'Invalid appointment'
            elif self.appointment.status != 'COMPLETED':
                errors['appointment'] = 'Can only create diagnosis for completed appointments'
            
            # Validate doctor is the same as appointment doctor (if appointment has doctor field)
            if hasattr(self.appointment, 'doctor') and self.doctor and self.doctor != self.appointment.doctor:
                errors['doctor'] = 'Diagnosis doctor must be the same as appointment doctor'
        
        # Validate symptoms length and content
        if len(self.symptoms.strip()) < 10:
            errors['symptoms'] = 'Please provide more detailed symptoms description (minimum 10 characters)'
        
        # Validate diagnosis content
        if self.diagnosis:
            diagnosis_words = self.diagnosis.strip().split()
            if len(diagnosis_words) < 2:  # Reduced from 3 to 2 for flexibility
                errors['diagnosis'] = 'Diagnosis should be more descriptive (at least 2 words)'
        
        # Validate follow-up date
        if self.follow_up_required and not self.follow_up_date:
            errors['follow_up_date'] = 'Follow-up date is required when follow-up is needed'
        
        if self.follow_up_date and self.appointment and hasattr(self.appointment, 'appointment_date'):
            if self.follow_up_date <= self.appointment.appointment_date:
                errors['follow_up_date'] = 'Follow-up date must be after the appointment date'
        
        # Check for duplicate diagnosis for same appointment (only for new instances)
        if not self.pk and self.appointment:
            if Diagnosis.objects.filter(appointment=self.appointment).exists():
                errors['appointment'] = 'Diagnosis already exists for this appointment'
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_patient_info(self):
        """Get formatted patient information"""
        if self.appointment and hasattr(self.appointment, 'patient'):
            patient = self.appointment.patient
            # Use full_name instead of name, and calculate age
            age = "Unknown"
            if hasattr(patient, 'date_of_birth') and patient.date_of_birth:
                today = timezone.now().date()
                age = today.year - patient.date_of_birth.year - (
                    (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
                )
            return f"{patient.full_name} ({age} years)"
        return "Unknown Patient"

    def get_condition_summary(self):
        """Get condition summary"""
        if self.diagnosis:
            return f"{self.diagnosis[:50]}... ({self.get_severity_display()})"
        return "No diagnosis"

    def requires_immediate_attention(self):
        """Check if condition requires immediate attention"""
        return self.severity in ['HIGH', 'CRITICAL']

    def __str__(self):
        patient_name = "Unknown"
        if self.appointment and hasattr(self.appointment, 'patient'):
            patient_name = self.appointment.patient.full_name
        diagnosis_preview = self.diagnosis[:30] + "..." if self.diagnosis else "No diagnosis"
        return f"Diagnosis for {patient_name} - {diagnosis_preview}"


class Prescription(models.Model):
    FREQUENCY_CHOICES = [
        ('OD', 'Once Daily'),
        ('BD', 'Twice Daily'),
        ('TDS', 'Three Times Daily'),
        ('QID', 'Four Times Daily'),
        ('PRN', 'As Required'),
        ('STAT', 'Immediately'),
    ]

    DURATION_UNIT_CHOICES = [
        ('DAYS', 'Days'),
        ('WEEKS', 'Weeks'),
        ('MONTHS', 'Months'),
    ]

    # Medicine name validation
    medicine_validator = RegexValidator(
        regex=r'^[a-zA-Z0-9\s\-\.\(\)]{2,100}$',
        message='Medicine name can only contain letters, numbers, spaces, hyphens, dots and parentheses'
    )
    
    # Dosage validation
    dosage_validator = RegexValidator(
        regex=r'^[a-zA-Z0-9\s\-\.\/]{1,50}$',
        message='Dosage format: 500mg, 10ml, 1 tablet, etc.'
    )

    appointment = models.ForeignKey(
        'receptionist.Appointment',  # Use string reference
        on_delete=models.CASCADE,
        related_name='prescriptions',
        help_text="Select appointment for prescription"
    )
    
    doctor = models.ForeignKey(
        'adminapp.Staff',  # Use string reference
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'DOCTOR'},
        help_text="Prescribing doctor"
    )
    
    medicine_name = models.CharField(
        max_length=100,
        validators=[medicine_validator],
        help_text="Enter medicine name"
    )
    
    dosage = models.CharField(
        max_length=100,
        validators=[dosage_validator],
        help_text="Enter dosage (e.g., 500mg, 10ml, 1 tablet)"
    )
    
    frequency = models.CharField(
        max_length=10,
        choices=FREQUENCY_CHOICES,
        default='BD',
        help_text="Medication frequency"
    )
    
    duration = models.IntegerField(
        validators=[
            MinValueValidator(1, message='Duration must be at least 1'),
            MaxValueValidator(365, message='Duration cannot exceed 365')
        ],
        help_text="Treatment duration"
    )
    
    duration_unit = models.CharField(
        max_length=10,
        choices=DURATION_UNIT_CHOICES,
        default='DAYS',
        help_text="Duration unit"
    )
    
    quantity = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Quantity to dispense (e.g., 30 tablets, 100ml)"
    )
    
    instructions = models.TextField(
        blank=True,
        null=True,
        help_text="Special instructions for medication"
    )
    
    # System fields
    created_at = models.DateTimeField(default=timezone.now)
    
    is_active = models.BooleanField(
        default=True,
        help_text="Is this prescription currently active?"
    )
    
    is_controlled = models.BooleanField(
        default=False,
        help_text="Is this a controlled substance?"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Prescription"
        verbose_name_plural = "Prescriptions"
        indexes = [
            models.Index(fields=['appointment']),
            models.Index(fields=['doctor']),
            models.Index(fields=['medicine_name']),
        ]

    def clean(self):
        """Prescription validation"""
        errors = {}
        
        # Validate appointment exists
        if self.appointment:
            # Check if appointment has diagnosis (relaxed validation)
            if not hasattr(self.appointment, 'diagnosis'):
                # Just a warning, not an error - allow prescriptions without diagnosis
                pass
            
            # Validate doctor is same as appointment doctor (if appointment has doctor field)
            if hasattr(self.appointment, 'doctor') and self.doctor and self.doctor != self.appointment.doctor:
                errors['doctor'] = 'Prescribing doctor must be the same as appointment doctor'
        
        # Validate medicine name
        if self.medicine_name:
            medicine_lower = self.medicine_name.lower()
            
            # Auto-detect controlled substances
            restricted_medicines = ['morphine', 'oxycodone', 'fentanyl', 'amphetamine']
            if any(med in medicine_lower for med in restricted_medicines):
                self.is_controlled = True
            
            # Validate duration for antibiotics (suggestion, not error)
            if 'antibiotic' in medicine_lower and self.duration < 5 and self.duration_unit == 'DAYS':
                # Make this a warning, not an error
                pass
        
        # Validate frequency and duration combination
        if self.frequency == 'STAT' and self.duration > 1:
            errors['duration'] = 'STAT medications are for single use only'
        
        # Check for duplicate prescriptions for same appointment
        if self.appointment and self.medicine_name:
            duplicate_prescriptions = Prescription.objects.filter(
                appointment=self.appointment,
                medicine_name__iexact=self.medicine_name
            ).exclude(pk=self.pk)
            
            if duplicate_prescriptions.exists():
                errors['medicine_name'] = f'{self.medicine_name} is already prescribed for this appointment'
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_duration_display(self):
        """Get formatted duration"""
        return f"{self.duration} {self.get_duration_unit_display().lower()}"

    def get_frequency_display_full(self):
        """Get full frequency display"""
        return dict(self.FREQUENCY_CHOICES).get(self.frequency, self.frequency)

    def is_long_term(self):
        """Check if this is a long-term prescription"""
        return (self.duration_unit == 'MONTHS' and self.duration > 1) or \
               (self.duration_unit == 'WEEKS' and self.duration > 4)

    def __str__(self):
        return f"{self.medicine_name} - {self.dosage} ({self.get_frequency_display_full()})"


class LabRequest(models.Model):
    TEST_TYPE_CHOICES = [
        ('BLOOD_TEST', 'Blood Test'),
        ('URINE_TEST', 'Urine Test'),
        ('IMAGING', 'Imaging'),
        ('BIOPSY', 'Biopsy'),
        ('CULTURE', 'Culture'),
        ('OTHER', 'Other'),
    ]

    STATUS_CHOICES = [
        ('REQUESTED', 'Requested'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('FAILED', 'Failed'),
    ]

    PRIORITY_CHOICES = [
        ('ROUTINE', 'Routine'),
        ('URGENT', 'Urgent'),
        ('STAT', 'STAT (Immediate)'),
    ]

    appointment = models.ForeignKey(
        'receptionist.Appointment',  # Use string reference
        on_delete=models.CASCADE,
        related_name='lab_requests',
        help_text="Select appointment for lab request"
    )
    
    doctor = models.ForeignKey(
        'adminapp.Staff',  # Use string reference
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'DOCTOR'},
        help_text="Requesting doctor"
    )
    
    test_name = models.CharField(
        max_length=100,
        help_text="Name of the test"
    )
    
    test_type = models.CharField(
        max_length=20,
        choices=TEST_TYPE_CHOICES,
        default='BLOOD_TEST',
        help_text="Type of test"
    )
    
    test_description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed test description and instructions"
    )
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default="REQUESTED",
        help_text="Test status"
    )
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='ROUTINE',
        help_text="Test priority"
    )
    
    # Additional fields
    specimen_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Type of specimen required (e.g., Blood, Urine, Tissue)"
    )
    
    special_instructions = models.TextField(
        blank=True,
        null=True,
        help_text="Any special instructions for the lab"
    )
    
    # System fields
    requested_date = models.DateTimeField(default=timezone.now)
    completed_date = models.DateTimeField(blank=True, null=True)
    
    is_fasting_required = models.BooleanField(
        default=False,
        help_text="Is fasting required for this test?"
    )
    
    estimated_duration = models.IntegerField(
        default=60,
        validators=[MinValueValidator(1), MaxValueValidator(1440)],
        help_text="Estimated test duration in minutes"
    )

    class Meta:
        ordering = ['-requested_date']
        verbose_name = "Lab Request"
        verbose_name_plural = "Lab Requests"
        indexes = [
            models.Index(fields=['appointment']),
            models.Index(fields=['doctor']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
        ]

    def clean(self):
        """Lab request validation"""
        errors = {}
        
        # Validate appointment exists
        if self.appointment:
            # Check if appointment has diagnosis (relaxed validation)
            if not hasattr(self.appointment, 'diagnosis'):
                # Just a warning, not an error - allow lab requests without diagnosis
                pass
            
            # Validate doctor is same as appointment doctor (if appointment has doctor field)
            if hasattr(self.appointment, 'doctor') and self.doctor and self.doctor != self.appointment.doctor:
                errors['doctor'] = 'Requesting doctor must be the same as appointment doctor'
        
        # Validate test name
        if len(self.test_name.strip()) < 2:
            errors['test_name'] = 'Test name must be at least 2 characters long'
        
        # Validate status transitions (only for existing instances)
        if self.pk:
            try:
                original = LabRequest.objects.get(pk=self.pk)
                if original.status == 'COMPLETED' and self.status != 'COMPLETED':
                    errors['status'] = 'Cannot change status from completed'
                if original.status == 'CANCELLED' and self.status != 'CANCELLED':
                    errors['status'] = 'Cannot change status from cancelled'
            except LabRequest.DoesNotExist:
                pass
        
        # Validate completed date
        if self.status == 'COMPLETED' and not self.completed_date:
            self.completed_date = timezone.now()
        elif self.status != 'COMPLETED' and self.completed_date:
            errors['completed_date'] = 'Completed date can only be set for completed tests'
        
        # Auto-detect fasting requirement for specific tests
        if self.test_name:
            fasting_tests = ['blood glucose', 'lipid profile', 'cholesterol', 'fasting']
            if any(test in self.test_name.lower() for test in fasting_tests):
                self.is_fasting_required = True
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_patient_info(self):
        """Get formatted patient information"""
        if self.appointment and hasattr(self.appointment, 'patient'):
            patient = self.appointment.patient
            age = "Unknown"
            if hasattr(patient, 'date_of_birth') and patient.date_of_birth:
                today = timezone.now().date()
                age = today.year - patient.date_of_birth.year - (
                    (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
                )
            return f"{patient.full_name} ({age} years)"
        return "Unknown Patient"

    def get_test_info(self):
        """Get formatted test information"""
        return f"{self.test_name} ({self.get_test_type_display()})"

    def is_urgent(self):
        """Check if test is urgent"""
        return self.priority in ['URGENT', 'STAT']

    def get_turnaround_time(self):
        """Calculate turnaround time"""
        if self.completed_date and self.requested_date:
            return self.completed_date - self.requested_date
        return None

    def can_be_cancelled(self):
        """Check if test can be cancelled"""
        return self.status in ['REQUESTED', 'IN_PROGRESS']

    def mark_completed(self):
        """Mark test as completed"""
        if self.status != 'COMPLETED':
            self.status = 'COMPLETED'
            self.completed_date = timezone.now()
            self.save()

    def __str__(self):
        patient_name = "Unknown"
        if self.appointment and hasattr(self.appointment, 'patient'):
            patient_name = self.appointment.patient.name
        return f"{self.test_name} - {patient_name}"