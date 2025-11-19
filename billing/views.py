from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum, Q
from .models import Billing
from .serializers import BillingSerializer
from rest_framework.permissions import IsAuthenticated
class BillingViewSet(viewsets.ModelViewSet):
    queryset = Billing.objects.all()
    serializer_class = BillingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Billing.objects.all()
        patient_id = self.request.query_params.get('patient_id')
        payment_status = self.request.query_params.get('payment_status')
        is_overdue = self.request.query_params.get('is_overdue')
        
        if patient_id: queryset = queryset.filter(patient_id=patient_id)
        if payment_status: queryset = queryset.filter(payment_status=payment_status)
        if is_overdue == 'true': queryset = queryset.filter(due_date__lt=timezone.now().date(), payment_status__in=['PENDING', 'PARTIAL'])
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def add_payment(self, request, pk=None):
        billing = self.get_object()
        amount = request.data.get('amount')
        method = request.data.get('payment_method')
        notes = request.data.get('notes', '')
        
        try:
            billing.add_payment(float(amount), method, notes)
            return Response({'status': 'Payment added successfully'})
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        billing = self.get_object()
        method = request.data.get('payment_method', 'CASH')
        notes = request.data.get('notes', '')
        
        billing.mark_as_paid(method, notes)
        return Response({'status': 'Bill marked as paid'})
    
    @action(detail=True, methods=['post'])
    def apply_discount(self, request, pk=None):
        billing = self.get_object()
        discount_amount = request.data.get('discount_amount')
        reason = request.data.get('reason', '')
        
        try:
            billing.apply_discount(float(discount_amount), reason)
            return Response({'status': 'Discount applied successfully'})
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        total_revenue = Billing.get_total_revenue()
        pending_bills = Billing.get_pending_bills().count()
        overdue_bills = Billing.get_overdue_bills().count()
        today_revenue = Billing.get_total_revenue(timezone.now().date(), timezone.now().date())
        
        return Response({
            'total_revenue': total_revenue,
            'pending_bills': pending_bills,
            'overdue_bills': overdue_bills,
            'today_revenue': today_revenue
        })
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        overdue_bills = Billing.get_overdue_bills()
        serializer = self.get_serializer(overdue_bills, many=True)
        return Response(serializer.data)