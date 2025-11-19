from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, F  # Added F import
from .models import MedicineIssue, MedicineInventory
from .serializers import MedicineIssueSerializer, MedicineInventorySerializer
from rest_framework.permissions import IsAuthenticated
class MedicineIssueViewSet(viewsets.ModelViewSet):
    queryset = MedicineIssue.objects.all()
    serializer_class = MedicineIssueSerializer
    permission_classes = [IsAuthenticated]

    
    def get_queryset(self):
        queryset = MedicineIssue.objects.all()
        pharmacist_id = self.request.query_params.get('pharmacist_id')
        status = self.request.query_params.get('status')
        payment_status = self.request.query_params.get('payment_status')
        is_controlled = self.request.query_params.get('is_controlled')
        
        if pharmacist_id: queryset = queryset.filter(pharmacist_id=pharmacist_id)
        if status: queryset = queryset.filter(status=status)
        if payment_status: queryset = queryset.filter(payment_status=payment_status)
        if is_controlled: queryset = queryset.filter(is_controlled_substance=(is_controlled.lower() == 'true'))
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def mark_issued(self, request, pk=None):
        medicine_issue = self.get_object()
        medicine_issue.status = 'ISSUED'
        medicine_issue.issued = True
        medicine_issue.issue_date = timezone.now().date()
        medicine_issue.issue_time = timezone.now().time()
        medicine_issue.save()
        return Response({'status': 'Medicine marked as issued'})
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        medicine_issue = self.get_object()
        medicine_issue.payment_status = 'PAID'
        medicine_issue.save()
        return Response({'status': 'Payment marked as paid'})
    
    @action(detail=True, methods=['post'])
    def add_instructions(self, request, pk=None):
        medicine_issue = self.get_object()
        instructions = request.data.get('instructions', '')
        medicine_issue.special_instructions = instructions
        medicine_issue.instructions_given = True
        medicine_issue.save()
        return Response({'status': 'Instructions added'})
    
    @action(detail=False, methods=['get'])
    def pending_issues(self, request):
        pending_issues = MedicineIssue.objects.filter(status='PENDING')
        serializer = self.get_serializer(pending_issues, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def controlled_substances(self, request):
        controlled_issues = MedicineIssue.objects.filter(is_controlled_substance=True)
        serializer = self.get_serializer(controlled_issues, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def unpaid_issues(self, request):
        unpaid_issues = MedicineIssue.objects.filter(payment_status='PENDING', status='ISSUED')
        serializer = self.get_serializer(unpaid_issues, many=True)
        return Response(serializer.data)

class MedicineInventoryViewSet(viewsets.ModelViewSet):
    queryset = MedicineInventory.objects.all()
    serializer_class = MedicineInventorySerializer
    permission_classes = [IsAuthenticated]

    
    def get_queryset(self):
        queryset = MedicineInventory.objects.all()
        category = self.request.query_params.get('category')
        needs_restock = self.request.query_params.get('needs_restock')
        is_controlled = self.request.query_params.get('is_controlled')
        medicine_name = self.request.query_params.get('medicine_name')
        
        if category: queryset = queryset.filter(category=category)
        if needs_restock == 'true': queryset = queryset.filter(quantity_in_stock__lte=F('reorder_level'))  # Fixed line 83
        if is_controlled: queryset = queryset.filter(is_controlled=(is_controlled.lower() == 'true'))
        if medicine_name: queryset = queryset.filter(medicine_name__icontains=medicine_name)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def update_stock(self, request, pk=None):
        inventory = self.get_object()
        new_quantity = request.data.get('quantity')
        if new_quantity is not None:
            inventory.quantity_in_stock = new_quantity
            inventory.last_restocked = timezone.now().date()
            inventory.save()
            return Response({'status': 'Stock updated successfully'})
        return Response({'error': 'Quantity is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_stock(self, request, pk=None):
        inventory = self.get_object()
        add_quantity = request.data.get('quantity')
        if add_quantity is not None:
            inventory.quantity_in_stock += add_quantity
            inventory.last_restocked = timezone.now().date()
            inventory.save()
            return Response({'status': f'Added {add_quantity} units to stock'})
        return Response({'error': 'Quantity is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        low_stock = MedicineInventory.objects.filter(quantity_in_stock__lte=F('reorder_level'))  # Fixed here too
        serializer = self.get_serializer(low_stock, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        soon_date = timezone.now().date() + timezone.timedelta(days=30)
        expiring_soon = MedicineInventory.objects.filter(expiry_date__lte=soon_date)
        serializer = self.get_serializer(expiring_soon, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        categories = [{'value': choice[0], 'label': choice[1]} for choice in MedicineInventory.CATEGORY_CHOICES]
        return Response(categories)