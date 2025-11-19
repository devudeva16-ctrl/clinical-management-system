from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

class LabReport(models.Model):
    REPORT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]

    RESULT_STATUS_CHOICES = [
        ('NORMAL', 'Normal'),
        ('ABNORMAL', 'Abnormal'),
        ('CRITICAL', 'Critical'),
        ('INCONCLUSIVE', 'Inconclusive'),
    ]

    PRIORITY_CHOICES = [
        ('ROUTINE', 'Routine'),
        ('URGENT', 'Urgent'),
        ('STAT', 'STAT (Immediate)'),
    ]

    lab_request = models.OneToOneField(
        'doctor.LabRequest',  # Use string reference
        on_delete=models.CASCADE,
        related_name='lab_report',
        help_text="Select lab request for this report"
    )
    
    technician = models.ForeignKey(
        'adminapp.Staff',  # Use string reference
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'LABTECH'},
        help_text="Lab technician performing the test"
    )
    
    result_file = models.FileField(
        upload_to="lab_reports/",
        blank=True,
        null=True,
        help_text="Upload test result file (PDF, Image, Document)"
    )
    
    results = models.TextField(
        blank=True,
        null=True,
        validators=[MinLengthValidator(10, message='Results must be at least 10 characters long')],
        help_text="Detailed test results and findings"
    )
    
    comments = models.TextField(
        blank=True,
        null=True,
        help_text="Technician comments and observations"
    )
    
    status = models.CharField(
        max_length=20,
        choices=REPORT_STATUS_CHOICES,
        default="PENDING",
        help_text="Current report status"
    )
    
    result_status = models.CharField(
        max_length=20,
        choices=RESULT_STATUS_CHOICES,
        blank=True,
        null=True,
        help_text="Overall result status"
    )
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='ROUTINE',
        help_text="Report priority level"
    )
    
    # Test details
    test_date = models.DateTimeField(
        default=timezone.now,
        help_text="Date and time when test was performed"
    )
    
    completed_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date and time when report was completed"
    )
    
    verified_by = models.ForeignKey(
        'adminapp.Staff',  # Use string reference
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        limit_choices_to={'role': 'DOCTOR'},
        related_name='verified_reports',
        help_text="Doctor who verified the report"
    )
    
    verification_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date and time when report was verified"
    )
    
    verification_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Verification notes from doctor"
    )
    
    # Quantitative results
    normal_range_min = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Minimum normal range value"
    )
    
    normal_range_max = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Maximum normal range value"
    )
    
    measured_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Measured test value"
    )
    
    unit = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Measurement unit (e.g., mg/dL, mmol/L)"
    )
    
    # Quality control
    is_quality_controlled = models.BooleanField(
        default=False,
        help_text="Whether quality control was performed"
    )
    
    quality_control_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Quality control notes and observations"
    )
    
    instrument_used = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Instrument used for testing"
    )
    
    # System fields
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    
    is_critical_result = models.BooleanField(
        default=False,
        help_text="Whether this is a critical result that requires immediate attention"
    )
    
    critical_result_acknowledged = models.BooleanField(
        default=False,
        help_text="Whether critical result was acknowledged by doctor"
    )
    
    critical_result_acknowledged_by = models.ForeignKey(
        'adminapp.Staff',  # Use string reference
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='acknowledged_critical_results',
        limit_choices_to={'role': 'DOCTOR'},
        help_text="Doctor who acknowledged critical result"
    )
    
    critical_result_acknowledged_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date and time when critical result was acknowledged"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Lab Report"
        verbose_name_plural = "Lab Reports"
        indexes = [
            models.Index(fields=['lab_request']),
            models.Index(fields=['technician']),
            models.Index(fields=['status']),
            models.Index(fields=['test_date']),
            models.Index(fields=['result_status']),
        ]

    def clean(self):
        """Comprehensive lab report validation"""
        errors = {}
        
        # Validate technician role
        if self.technician and self.technician.role != 'LABTECH':
            errors['technician'] = 'Only lab technician staff can create lab reports'
        
        # Validate status transitions
        if self.pk:  # Only for existing instances
            try:
                original = LabReport.objects.get(pk=self.pk)
                
                # Cannot change status from completed/verified without proper permissions
                if original.status in ['COMPLETED', 'VERIFIED'] and self.status not in ['COMPLETED', 'VERIFIED']:
                    errors['status'] = 'Cannot change status from completed/verified'
                
                # Cannot change status from rejected
                if original.status == 'REJECTED' and self.status != 'REJECTED':
                    errors['status'] = 'Cannot change status from rejected'
            except LabReport.DoesNotExist:
                pass
        
        # Validate completed date
        if self.status == 'COMPLETED' and not self.completed_date:
            self.completed_date = timezone.now()
        elif self.status != 'COMPLETED' and self.completed_date:
            errors['completed_date'] = 'Completed date can only be set for completed reports'
        
        # Validate verification
        if self.status == 'VERIFIED':
            if not self.verified_by:
                errors['verified_by'] = 'Verified by doctor is required for verified reports'
            if not self.verification_date:
                self.verification_date = timezone.now()
        elif self.status != 'VERIFIED' and self.verified_by:
            errors['verified_by'] = 'Verified by can only be set for verified reports'
        
        # Validate results
        if self.status in ['COMPLETED', 'VERIFIED']:
            if not self.results and not self.result_file:
                errors['results'] = 'Results or result file is required for completed reports'
            
            if not self.result_status:
                errors['result_status'] = 'Result status is required for completed reports'
        
        # Validate quantitative results
        if self.measured_value is not None:
            if self.normal_range_min is None or self.normal_range_max is None:
                errors['measured_value'] = 'Normal range must be specified when providing measured value'
            else:
                if self.measured_value < self.normal_range_min or self.measured_value > self.normal_range_max:
                    self.result_status = 'ABNORMAL'
                    
                    # Check for critical values (example thresholds)
                    critical_threshold = 0.2  # 20% outside normal range
                    range_width = self.normal_range_max - self.normal_range_min
                    
                    if (self.measured_value < self.normal_range_min - (range_width * critical_threshold) or
                        self.measured_value > self.normal_range_max + (range_width * critical_threshold)):
                        self.is_critical_result = True
                        self.result_status = 'CRITICAL'
                else:
                    self.result_status = 'NORMAL'
                    self.is_critical_result = False
        
        # Validate critical results
        if self.is_critical_result and self.status in ['COMPLETED', 'VERIFIED']:
            if not self.critical_result_acknowledged:
                # This is a warning, not an error
                pass
        
        # Validate test date
        if self.test_date and self.test_date > timezone.now():
            errors['test_date'] = 'Test date cannot be in the future'
        
        if self.lab_request and self.test_date:
            if self.test_date.date() < self.lab_request.requested_date.date():
                errors['test_date'] = 'Test date cannot be before lab request date'
        
        # Validate file type if provided
        if self.result_file:
            valid_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx', '.txt']
            if not any(self.result_file.name.lower().endswith(ext) for ext in valid_extensions):
                errors['result_file'] = 'Invalid file type. Allowed: PDF, Images, Documents, Text files'
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Override save to run validations and auto-update related models"""
        self.full_clean()
        
        # Auto-update lab request status when report is completed
        if self.status == 'COMPLETED' and hasattr(self.lab_request, 'status'):
            if self.lab_request.status != 'COMPLETED':
                self.lab_request.status = 'COMPLETED'
                self.lab_request.completed_date = timezone.now()
                self.lab_request.save()
        
        # Auto-set priority from lab request
        if not self.priority and self.lab_request and hasattr(self.lab_request, 'priority'):
            self.priority = self.lab_request.priority
        
        super().save(*args, **kwargs)

    def get_patient_info(self):
        """Get formatted patient information"""
        if (self.lab_request and 
            hasattr(self.lab_request, 'appointment') and 
            hasattr(self.lab_request.appointment, 'patient') and
            hasattr(self.lab_request.appointment.patient, 'full_name')):
            return f"{self.lab_request.appointment.patient.full_name}"
        return "Unknown Patient"

    def get_test_info(self):
        """Get formatted test information"""
        if self.lab_request:
            test_name = self.lab_request.test_name if hasattr(self.lab_request, 'test_name') else "Unknown Test"
            test_type = self.lab_request.get_test_type_display() if hasattr(self.lab_request, 'get_test_type_display') else "Unknown Type"
            return f"{test_name} ({test_type})"
        return "Unknown Test"

    def get_doctor_info(self):
        """Get formatted doctor information"""
        if (self.lab_request and 
            hasattr(self.lab_request, 'doctor') and 
            hasattr(self.lab_request.doctor, 'full_name')):
            return f"Dr. {self.lab_request.doctor.full_name}"
        return "Unknown Doctor"

    def is_overdue(self):
        """Check if report is overdue"""
        if self.status in ['PENDING', 'IN_PROGRESS']:
            # Consider overdue if pending for more than 24 hours for urgent, 72 hours for routine
            time_limit = 24 if self.priority in ['URGENT', 'STAT'] else 72
            time_elapsed = (timezone.now() - self.created_at).total_seconds() / 3600
            return time_elapsed > time_limit
        return False

    def can_be_verified(self):
        """Check if report can be verified"""
        return self.status == 'COMPLETED' and not self.verified_by

    def mark_verified(self, verified_by, notes=""):
        """Mark report as verified by doctor"""
        if self.can_be_verified():
            self.status = 'VERIFIED'
            self.verified_by = verified_by
            self.verification_date = timezone.now()
            self.verification_notes = notes
            self.save()

    def mark_critical_acknowledged(self, acknowledged_by):
        """Mark critical result as acknowledged"""
        if self.is_critical_result and not self.critical_result_acknowledged:
            self.critical_result_acknowledged = True
            self.critical_result_acknowledged_by = acknowledged_by
            self.critical_result_acknowledged_date = timezone.now()
            self.save()

    def get_turnaround_time(self):
        """Calculate turnaround time in hours"""
        if self.completed_date and self.created_at:
            return (self.completed_date - self.created_at).total_seconds() / 3600
        return None

    def is_urgent(self):
        """Check if this is an urgent test"""
        return self.priority in ['URGENT', 'STAT']

    def __str__(self):
        patient_info = self.get_patient_info()
        test_info = self.get_test_info()
        return f"Report for {test_info} - {patient_info}"


class LabEquipment(models.Model):
    EQUIPMENT_STATUS_CHOICES = [
        ('OPERATIONAL', 'Operational'),
        ('MAINTENANCE', 'Under Maintenance'),
        ('CALIBRATION', 'Needs Calibration'),
        ('OUT_OF_SERVICE', 'Out of Service'),
    ]

    CALIBRATION_FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
    ]

    name = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(2, message='Name must be at least 2 characters long')],
        help_text="Equipment name"
    )
    
    model = models.CharField(
        max_length=100,
        help_text="Equipment model"
    )
    
    serial_number = models.CharField(
        max_length=50,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z0-9\-]{3,50}$',
                message='Serial number must be 3-50 characters (letters, numbers, hyphens)'
            )
        ],
        help_text="Equipment serial number"
    )
    
    manufacturer = models.CharField(
        max_length=100,
        help_text="Equipment manufacturer"
    )
    
    status = models.CharField(
        max_length=20,
        choices=EQUIPMENT_STATUS_CHOICES,
        default='OPERATIONAL',
        help_text="Current equipment status"
    )
    
    calibration_due_date = models.DateField(
        help_text="Next calibration due date"
    )
    
    calibration_frequency = models.CharField(
        max_length=20,
        choices=CALIBRATION_FREQUENCY_CHOICES,
        default='MONTHLY',
        help_text="Calibration frequency"
    )
    
    last_calibration_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date of last calibration"
    )
    
    last_maintenance_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date of last maintenance"
    )
    
    next_maintenance_date = models.DateField(
        blank=True,
        null=True,
        help_text="Next maintenance due date"
    )
    
    location = models.CharField(
        max_length=100,
        help_text="Equipment location in lab"
    )
    
    is_critical_equipment = models.BooleanField(
        default=False,
        help_text="Whether this is critical equipment"
    )
    
    # System fields
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional equipment notes"
    )

    class Meta:
        ordering = ['name']
        verbose_name = "Lab Equipment"
        verbose_name_plural = "Lab Equipment"
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['serial_number']),
            models.Index(fields=['status']),
        ]

    def clean(self):
        """Lab equipment validation"""
        errors = {}
        
        # Validate calibration dates
        if self.calibration_due_date and self.calibration_due_date < timezone.now().date():
            errors['calibration_due_date'] = 'Calibration due date cannot be in the past'
        
        if self.last_calibration_date and self.last_calibration_date > timezone.now().date():
            errors['last_calibration_date'] = 'Last calibration date cannot be in the future'
        
        if self.next_maintenance_date and self.next_maintenance_date < timezone.now().date():
            errors['next_maintenance_date'] = 'Next maintenance date cannot be in the past'
        
        if self.last_maintenance_date and self.last_maintenance_date > timezone.now().date():
            errors['last_maintenance_date'] = 'Last maintenance date cannot be in the future'
        
        # Validate serial number format
        if self.serial_number and LabEquipment.objects.filter(serial_number=self.serial_number).exclude(pk=self.pk).exists():
            errors['serial_number'] = 'Equipment with this serial number already exists'
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def needs_calibration(self):
        """Check if equipment needs calibration"""
        return self.calibration_due_date <= timezone.now().date()

    def needs_maintenance(self):
        """Check if equipment needs maintenance"""
        return self.next_maintenance_date and self.next_maintenance_date <= timezone.now().date()

    def is_operational(self):
        """Check if equipment is operational"""
        return self.status == 'OPERATIONAL'

    def get_calibration_status(self):
        """Get calibration status"""
        if self.needs_calibration():
            return 'OVERDUE'
        elif (self.calibration_due_date - timezone.now().date()).days <= 7:
            return 'DUE_SOON'
        else:
            return 'OK'

    def __str__(self):
        return f"{self.name} - {self.model} ({self.serial_number})"