from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

class Billing(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('PARTIAL', 'Partially Paid'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('CARD', 'Credit/Debit Card'),
        ('UPI', 'UPI'),
        ('INSURANCE', 'Insurance'),
        ('OTHER', 'Other'),
    ]

    patient = models.ForeignKey(
        'receptionist.Patient', 
        on_delete=models.CASCADE,
        related_name='bills',
        help_text="Select patient for billing"
    )
    
    bill_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text="Auto-generated bill number"
    )
    
    consultation_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=300.00,
        help_text="Consultation fee"
    )
    
    medicine_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Total medicine cost"
    )
    
    lab_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Total laboratory test costs"
    )
    
    other_charges = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Other miscellaneous charges"
    )
    
    discount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Discount amount"
    )
    
    tax_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Tax amount"
    )
    
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Final total amount after calculations"
    )
    
    amount_paid = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Amount paid by patient"
    )
    
    balance_due = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Remaining balance to be paid"
    )
    
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING',
        help_text="Current payment status"
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        null=True,
        help_text="Payment method used"
    )
    
    prescription = models.ForeignKey(
        'doctor.Prescription',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bills',
        help_text="Related prescription"
    )
    
    lab_requests = models.ManyToManyField(
        'doctor.LabRequest',
        blank=True,
        related_name='bills',
        help_text="Related lab tests"
    )
    
    billing_date = models.DateField(
        default=timezone.now,
        help_text="Date when bill was created"
    )
    
    due_date = models.DateField(
        blank=True,
        null=True,
        help_text="Due date for payment"
    )
    
    payment_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date when payment was made"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Additional notes or comments"
    )
    
    created_by = models.ForeignKey(
        'adminapp.Staff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Staff member who created the bill"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Billing"
        verbose_name_plural = "Billing Records"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['bill_number']),
            models.Index(fields=['patient', 'billing_date']),
            models.Index(fields=['payment_status']),
        ]

    def __str__(self):
        return f"Bill #{self.bill_number} - {self.patient.name} - ₹{self.total_amount}"

    def clean(self):
        """Model-level validation"""
        errors = {}
        
        # Validate amounts are non-negative
        if self.consultation_fee < 0:
            errors['consultation_fee'] = 'Consultation fee cannot be negative'
        
        if self.medicine_cost < 0:
            errors['medicine_cost'] = 'Medicine cost cannot be negative'
        
        if self.lab_cost < 0:
            errors['lab_cost'] = 'Lab cost cannot be negative'
        
        if self.other_charges < 0:
            errors['other_charges'] = 'Other charges cannot be negative'
        
        if self.discount < 0:
            errors['discount'] = 'Discount cannot be negative'
        
        if self.tax_amount < 0:
            errors['tax_amount'] = 'Tax amount cannot be negative'
        
        # Validate amount paid doesn't exceed total amount
        if self.amount_paid > self.total_amount:
            errors['amount_paid'] = 'Amount paid cannot exceed total amount'
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Override save to generate bill number and calculate totals"""
        # Generate bill number if not set
        if not self.bill_number:
            self.bill_number = self.generate_bill_number()
        
        # Calculate totals before saving
        self.calculate_total()
        
        # Set due date if not set (default: 15 days from billing date)
        if not self.due_date:
            self.due_date = self.billing_date + timezone.timedelta(days=15)
        
        self.full_clean()
        super().save(*args, **kwargs)

    def generate_bill_number(self):
        """Generate unique bill number in format BILL-YYYYMMDD-XXXX"""
        today = timezone.now().date()
        date_str = today.strftime('%Y%m%d')
        
        # Count bills for today to get sequence number
        today_bills_count = Billing.objects.filter(
            created_at__date=today
        ).count()
        
        sequence = today_bills_count + 1
        return f"BILL-{date_str}-{sequence:04d}"

    def calculate_total(self):
        """Calculate total amount, balance due, and update payment status"""
        # Calculate subtotal
        subtotal = (
            self.consultation_fee + 
            self.medicine_cost + 
            self.lab_cost + 
            self.other_charges
        )
        
        # Apply discount
        discounted_amount = subtotal - self.discount
        
        # Calculate final total (subtotal - discount + tax)
        self.total_amount = discounted_amount + self.tax_amount
        
        # Ensure total amount is not negative
        if self.total_amount < 0:
            self.total_amount = 0
        
        # Calculate balance due
        self.balance_due = self.total_amount - self.amount_paid
        
        # Update payment status based on amounts
        self.update_payment_status()

    def update_payment_status(self):
        """Update payment status based on amount paid and balance due"""
        if self.amount_paid == 0:
            self.payment_status = 'PENDING'
        elif self.amount_paid >= self.total_amount:
            self.payment_status = 'PAID'
            self.payment_date = timezone.now()
        elif self.amount_paid > 0:
            self.payment_status = 'PARTIAL'
        else:
            self.payment_status = 'PENDING'

    def add_payment(self, amount, method=None, notes=""):
        """Add a payment to the bill"""
        if amount <= 0:
            raise ValidationError("Payment amount must be positive")
        
        if amount > self.balance_due:
            raise ValidationError("Payment amount exceeds balance due")
        
        self.amount_paid += amount
        
        if method:
            self.payment_method = method
        
        if notes:
            self.notes = notes
        
        self.calculate_total()
        self.save()

    def mark_as_paid(self, method='CASH', notes=""):
        """Mark the bill as fully paid"""
        self.amount_paid = self.total_amount
        self.payment_method = method
        self.payment_status = 'PAID'
        self.payment_date = timezone.now()
        
        if notes:
            self.notes = notes
        
        self.calculate_total()
        self.save()

    def apply_discount(self, discount_amount, reason=""):
        """Apply discount to the bill"""
        if discount_amount <= 0:
            raise ValidationError("Discount amount must be positive")
        
        if discount_amount > self.total_amount:
            raise ValidationError("Discount cannot exceed total amount")
        
        self.discount = discount_amount
        
        if reason:
            current_notes = self.notes or ""
            self.notes = f"{current_notes}\nDiscount applied: {reason}".strip()
        
        self.calculate_total()
        self.save()

    @property
    def is_overdue(self):
        """Check if the bill is overdue"""
        if self.payment_status == 'PAID':
            return False
        return self.due_date and timezone.now().date() > self.due_date

    @property
    def days_overdue(self):
        """Calculate number of days overdue"""
        if not self.is_overdue:
            return 0
        return (timezone.now().date() - self.due_date).days

    @property
    def subtotal(self):
        """Calculate subtotal before discount and tax"""
        return (
            self.consultation_fee + 
            self.medicine_cost + 
            self.lab_cost + 
            self.other_charges
        )

    def get_bill_summary(self):
        """Get a summary of the bill"""
        return {
            'bill_number': self.bill_number,
            'patient': str(self.patient),
            'subtotal': float(self.subtotal),
            'discount': float(self.discount),
            'tax': float(self.tax_amount),
            'total': float(self.total_amount),
            'paid': float(self.amount_paid),
            'balance': float(self.balance_due),
            'status': self.payment_status,
            'is_overdue': self.is_overdue
        }

    @classmethod
    def get_pending_bills(cls):
        """Get all pending bills"""
        return cls.objects.filter(payment_status='PENDING')

    @classmethod
    def get_overdue_bills(cls):
        """Get all overdue bills"""
        today = timezone.now().date()
        return cls.objects.filter(
            payment_status__in=['PENDING', 'PARTIAL'],
            due_date__lt=today
        )

    @classmethod
    def get_total_revenue(cls, start_date=None, end_date=None):
        """Calculate total revenue for a period"""
        queryset = cls.objects.filter(payment_status='PAID')
        
        if start_date:
            queryset = queryset.filter(payment_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(payment_date__lte=end_date)
        
        return queryset.aggregate(total_revenue=models.Sum('total_amount'))['total_revenue'] or 0