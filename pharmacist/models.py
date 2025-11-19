from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


class MedicineIssue(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ISSUED', 'Issued'),
        ('PARTIAL', 'Partially Issued'),
        ('CANCELLED', 'Cancelled'),
        ('OUT_OF_STOCK', 'Out of Stock'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('INSURANCE', 'Insurance Covered'),
        ('WAIVED', 'Waived'),
    ]

    prescription = models.ForeignKey(
        'doctor.Prescription',
        on_delete=models.CASCADE,
        related_name='medicine_issues',
        help_text="Select prescription to issue"
    )
    
    pharmacist = models.ForeignKey(
        'adminapp.Staff',
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'PHARMACIST'},
        help_text="Issuing pharmacist"
    )
    
    issued = models.BooleanField(
        default=False,
        help_text="Whether medicine has been issued"
    )
    
    # CHANGED: Remove auto_now_add and use default
    issue_date = models.DateField(
        default=timezone.now,  # Changed from auto_now_add=True
        help_text="Date when medicine was issued"
    )
    
    issue_time = models.TimeField(
        default=timezone.now,  # Changed from auto_now_add=True
        help_text="Time when medicine was issued"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Current issuance status"
    )
    
    quantity_issued = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Actual quantity issued (e.g., 28 tablets, 100ml)"
    )
    
    batch_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z0-9\-]{3,50}$',
                message='Batch number must be 3-50 characters (letters, numbers, hyphens)'
            )
        ],
        help_text="Medicine batch number"
    )
    
    expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text="Medicine expiry date"
    )
    
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        help_text="Price per unit"
    )
    
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        help_text="Total price for issued quantity"
    )
    
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING',
        help_text="Payment status for the medicine"
    )
    
    instructions_given = models.BooleanField(
        default=False,
        help_text="Whether usage instructions were given to patient"
    )
    
    special_instructions = models.TextField(
        blank=True,
        null=True,
        help_text="Additional instructions for the patient"
    )
    
    side_effects_explained = models.BooleanField(
        default=False,
        help_text="Whether side effects were explained to patient"
    )
    
    # CHANGED: Remove auto_now_add and use default
    created_at = models.DateTimeField(default=timezone.now)  # Changed from auto_now_add=True
    updated_at = models.DateTimeField(default=timezone.now)  # Changed from auto_now=True
    
    is_controlled_substance = models.BooleanField(
        default=False,
        help_text="Whether this is a controlled substance"
    )
    
    controlled_substance_log = models.TextField(
        blank=True,
        null=True,
        help_text="Log for controlled substance tracking"
    )
    
    patient_signature_obtained = models.BooleanField(
        default=False,
        help_text="Whether patient signature was obtained (for controlled substances)"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Medicine Issue"
        verbose_name_plural = "Medicine Issues"
        indexes = [
            models.Index(fields=['prescription']),
            models.Index(fields=['pharmacist']),
            models.Index(fields=['status']),
            models.Index(fields=['issue_date']),
        ]

    def clean(self):
        """Comprehensive medicine issue validation"""
        errors = {}
        
        # Validate prescription exists and is active
        if self.prescription:
            if hasattr(self.prescription, 'is_active') and not self.prescription.is_active:
                errors['prescription'] = 'Cannot issue medicine for inactive prescription'
        else:
            errors['prescription'] = 'Prescription is required'
        
        # Validate pharmacist role
        if self.pharmacist and self.pharmacist.role != 'PHARMACIST':
            errors['pharmacist'] = 'Only pharmacist staff can issue medicines'
        
        # Validate status transitions
        if self.pk:  # Only for existing instances
            try:
                original = MedicineIssue.objects.get(pk=self.pk)
                if original.status == 'ISSUED' and self.status != 'ISSUED':
                    errors['status'] = 'Cannot change status from issued'
                if original.status == 'CANCELLED' and self.status != 'CANCELLED':
                    errors['status'] = 'Cannot change status from cancelled'
            except MedicineIssue.DoesNotExist:
                pass
        
        # Validate issued status
        if self.issued and not self.issue_date:
            errors['issued'] = 'Issue date must be set when medicine is issued'
        
        # Validate quantity issued
        if self.status == 'ISSUED' and not self.quantity_issued:
            errors['quantity_issued'] = 'Quantity issued is required when status is issued'
        
        # Validate batch number for issued medicines
        if self.status == 'ISSUED' and not self.batch_number:
            errors['batch_number'] = 'Batch number is required for issued medicines'
        
        # Validate expiry date
        if self.expiry_date and self.expiry_date <= timezone.now().date():
            errors['expiry_date'] = 'Medicine expiry date must be in the future'
        
        # Validate controlled substances
        if self.prescription and hasattr(self.prescription, 'is_controlled') and self.prescription.is_controlled:
            self.is_controlled_substance = True
            
            if self.status == 'ISSUED' and not self.patient_signature_obtained:
                errors['patient_signature_obtained'] = 'Patient signature is required for controlled substances'
            
            if self.status == 'ISSUED' and not self.controlled_substance_log:
                errors['controlled_substance_log'] = 'Controlled substance log is required'
        
        # Validate pricing
        if self.unit_price < 0:
            errors['unit_price'] = 'Unit price cannot be negative'
        
        if self.total_price < 0:
            errors['total_price'] = 'Total price cannot be negative'
        
        # Validate instructions were given
        if self.status == 'ISSUED' and not self.instructions_given:
            errors['instructions_given'] = 'Usage instructions must be given when issuing medicine'
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Override save to run validations and auto-calculate fields"""
        self.full_clean()
        
        # Auto-calculate total price if unit price and quantity are set
        if self.unit_price > 0 and self.quantity_issued:
            try:
                # Extract numeric value from quantity_issued (e.g., "30 tablets" -> 30)
                import re
                quantity_match = re.search(r'(\d+)', self.quantity_issued)
                if quantity_match:
                    quantity = int(quantity_match.group(1))
                    self.total_price = self.unit_price * quantity
            except (ValueError, TypeError):
                # If parsing fails, keep the existing total_price
                pass
        
        # Auto-set issued based on status
        if self.status == 'ISSUED':
            self.issued = True
            if not self.issue_date:
                self.issue_date = timezone.now().date()
            if not self.issue_time:
                self.issue_time = timezone.now().time()
        else:
            self.issued = False
        
        # Auto-set controlled substance flag
        if self.prescription and hasattr(self.prescription, 'is_controlled') and self.prescription.is_controlled:
            self.is_controlled_substance = True
        
        # Update updated_at timestamp manually
        self.updated_at = timezone.now()
        
        super().save(*args, **kwargs)

    # ... keep all your existing methods (get_patient_info, get_medicine_info, etc.) as they are ...


class MedicineInventory(models.Model):
    CATEGORY_CHOICES = [
        ('TABLET', 'Tablet'),
        ('CAPSULE', 'Capsule'),
        ('SYRUP', 'Syrup'),
        ('INJECTION', 'Injection'),
        ('OINTMENT', 'Ointment'),
        ('DROP', 'Drop'),
        ('INHALER', 'Inhaler'),
        ('OTHER', 'Other'),
    ]

    medicine_name = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9\s\-\.\(\)]{2,100}$',
                message='Medicine name can only contain letters, numbers, spaces, hyphens, dots and parentheses'
            )
        ],
        help_text="Medicine name"
    )
    
    generic_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Generic name of the medicine"
    )
    
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='TABLET',
        help_text="Medicine category"
    )
    
    batch_number = models.CharField(
        max_length=50,
        validators=[
            RegexValidator(
                regex=r'^[A-Z0-9\-]{3,50}$',
                message='Batch number must be 3-50 characters (letters, numbers, hyphens)'
            )
        ],
        help_text="Batch number"
    )
    
    expiry_date = models.DateField(
        help_text="Expiry date"
    )
    
    quantity_in_stock = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="Quantity currently in stock"
    )
    
    reorder_level = models.IntegerField(
        default=10,
        validators=[MinValueValidator(0)],
        help_text="Reorder level alert"
    )
    
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Price per unit"
    )
    
    supplier = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Medicine supplier"
    )
    
    is_controlled = models.BooleanField(
        default=False,
        help_text="Is this a controlled substance?"
    )
    
    # CHANGED: Remove auto_now_add and use default
    created_at = models.DateTimeField(default=timezone.now)  # Changed from auto_now_add=True
    updated_at = models.DateTimeField(default=timezone.now)  # Changed from auto_now=True
    
    last_restocked = models.DateField(
        blank=True,
        null=True,
        help_text="Date when last restocked"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes"
    )

    class Meta:
        ordering = ['medicine_name', 'expiry_date']
        verbose_name = "Medicine Inventory"
        verbose_name_plural = "Medicine Inventory"
        indexes = [
            models.Index(fields=['medicine_name']),
            models.Index(fields=['batch_number']),
            models.Index(fields=['expiry_date']),
        ]
        unique_together = ['medicine_name', 'batch_number']

    def clean(self):
        """Medicine inventory validation"""
        errors = {}
        
        # Validate expiry date
        if self.expiry_date and self.expiry_date <= timezone.now().date():
            errors['expiry_date'] = 'Expiry date must be in the future'
        
        # Validate quantity
        if self.quantity_in_stock < 0:
            errors['quantity_in_stock'] = 'Quantity cannot be negative'
        
        # Validate reorder level
        if self.reorder_level < 0:
            errors['reorder_level'] = 'Reorder level cannot be negative'
        
        # Validate unit price
        if self.unit_price <= 0:
            errors['unit_price'] = 'Unit price must be greater than 0'
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        # Update updated_at timestamp manually
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    # ... keep all your existing methods as they are ...

    def __str__(self):
        return f"{self.medicine_name} - Batch: {self.batch_number}"