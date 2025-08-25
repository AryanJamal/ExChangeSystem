from rest_framework import viewsets
from .models import *
from .serializers import *
from django.utils import timezone
from django.db.models import Q
from datetime import date
from rest_framework.permissions import IsAuthenticated

today = timezone.localdate()


# SafeType
class SafeTypeViewSet(viewsets.ModelViewSet):
    queryset = SafeType.objects.all()
    serializer_class = SafeTypeSerializer
    permission_classes = [IsAuthenticated]


# Partner
class PartnerViewSet(viewsets.ModelViewSet):
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
    permission_classes = [IsAuthenticated]


# SafePartner
class SafePartnerViewSet(viewsets.ModelViewSet):
    queryset = SafePartner.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ["POST", "PUT", "PATCH"]:
            return SafePartnerCreateSerializer
        return SafePartnerSerializer


# CryptoTransaction
class CryptoTransactionViewSet(viewsets.ModelViewSet):
    queryset = CryptoTransaction.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CryptoTransactionPostSerializer
        return CryptoTransactionGetSerializer

    def get_queryset(self):
        queryset = super().get_queryset()  # Start with the base queryset (all objects)

        # Get query parameters from the request
        search_query = self.request.query_params.get("search", None)
        status = self.request.query_params.get("status", None)
        partner_id = self.request.query_params.get(
            "partner_id", None
        )  # Renamed to match frontend param
        start_date_str = self.request.query_params.get("start_date", None)
        end_date_str = self.request.query_params.get("end_date", None)

        if any([search_query, status, partner_id, start_date_str, end_date_str]):
            # Apply search filter (client_name or partner name)
            if search_query:
                queryset = queryset.filter(
                    Q(client_name__icontains=search_query)
                    | Q(
                        partner__partner__name__icontains=search_query
                    )  # Assuming partner has a nested partner.name
                )

            # Apply status filter
            if status:
                queryset = queryset.filter(status=status)

            # Apply partner filter by ID
            if partner_id:
                queryset = queryset.filter(partner__id=partner_id)

            # Apply date range filter
            if start_date_str:
                try:
                    start_date = date.fromisoformat(start_date_str)
                    queryset = queryset.filter(created_at__date__gte=start_date)
                except ValueError:
                    # Handle invalid date format if necessary
                    pass

            if end_date_str:
                try:
                    end_date = date.fromisoformat(end_date_str)
                    queryset = queryset.filter(created_at__date__lte=end_date)
                except ValueError:
                    # Handle invalid date format if necessary
                    pass

            if end_date_str and not start_date_str:
                try:
                    end_date = date.fromisoformat(end_date_str)
                    queryset = queryset.filter(created_at__date=end_date)
                except ValueError:
                    # Handle invalid date format if necessary
                    pass
        else:
            queryset = queryset.filter(created_at__date=today)
        # You can add ordering here if you want default ordering
        # For example, order by creation date descending
        queryset = queryset.order_by("-created_at")

        return queryset


# TransferExchange
class TransferExchangeViewSet(viewsets.ModelViewSet):
    queryset = TransferExchange.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TransferExchangePostSerializer  # Use POST if you have one
        return TransferExchangeGetSerializer


# IncomingMoney
class IncomingMoneyViewSet(viewsets.ModelViewSet):
    queryset = IncomingMoney.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return IncomingMoneyPostSerializer
        if self.request.method == "PATCH":
            return IncomingMoneyStatusUpdateSerializer
        return IncomingMoneyGetSerializer

    def get_queryset(self):
        queryset = IncomingMoney.objects.all()
        query_params = self.request.query_params

        # Check if any filter parameters are provided.
        # This includes all the filters you previously defined.
        is_filtered = any(
            key in query_params
            for key in [
                "search",
                "status",
                "start_date",
                "end_date",
                "from_partner",
                "to_partner",
            ]
        )

        # If no filters are provided, default to today's records
        if not is_filtered:
            today = timezone.localdate()
            queryset = queryset.filter(created_at__date=today)

        # Apply search functionality
        search_query = query_params.get("search", "").strip()
        if search_query:
            queryset = queryset.filter(
                Q(from_partner__partner__name__icontains=search_query)
                | Q(to_partner__partner__name__icontains=search_query)
                | Q(to_name__icontains=search_query)
                | Q(to_number__icontains=search_query)
                | Q(money_amount__icontains=search_query)
            )

        # Apply other filters if they exist
        status = query_params.get("status", "").strip()
        if status:
            queryset = queryset.filter(status=status)

        start_date = query_params.get("start_date")
        end_date = query_params.get("end_date")
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        from_partner_id = query_params.get("from_partner")
        to_partner_id = query_params.get("to_partner")
        if from_partner_id:
            queryset = queryset.filter(from_partner__id=from_partner_id)
        if to_partner_id:
            queryset = queryset.filter(to_partner__id=to_partner_id)

        return queryset


# OutgoingMoney
class OutgoingMoneyViewSet(viewsets.ModelViewSet):
    queryset = OutgoingMoney.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return OutgoingMoneyPostSerializer
        return OutgoingMoneyGetSerializer

    def get_queryset(self):

        queryset = OutgoingMoney.objects.all()

        # Get query parameters from the request
        query_params = self.request.query_params

        is_filtered = any(
            key in query_params
            for key in [
                "search",
                "status",
                "start_date",
                "end_date",
                "from_partner",
                "to_partner",
            ]
        )

        # If no filters are provided, default to today's records
        if not is_filtered:
            today = timezone.localdate()
            queryset = queryset.filter(created_at__date=today)

        # 1. Handle search query
        search_query = query_params.get("search", None)
        if search_query:
            # Use Q objects to perform a logical OR search across multiple fields
            queryset = queryset.filter(
                Q(from_partner__partner__name__icontains=search_query)
                | Q(to_partner__partner__name__icontains=search_query)
                | Q(from_name__icontains=search_query)
                | Q(from_number__icontains=search_query)
                | Q(money_amount__icontains=search_query)
            )

        # 2. Handle status filter
        status = query_params.get("status", None)
        if status:
            queryset = queryset.filter(status=status)

        # 3. Handle date range filters
        start_date = query_params.get("start_date", None)
        end_date = query_params.get("end_date", None)

        if start_date:
            # Filter for transactions on or after the start date
            queryset = queryset.filter(created_at__gte=start_date)

        if end_date:
            # Filter for transactions on or before the end date
            queryset = queryset.filter(created_at__lte=end_date)

        # 4. Handle partner filters
        from_partner_id = query_params.get("from_partner", None)
        if from_partner_id:
            queryset = queryset.filter(from_partner__id=from_partner_id)

        to_partner_id = query_params.get("to_partner", None)
        if to_partner_id:
            queryset = queryset.filter(to_partner__id=to_partner_id)

        return queryset


# SafeTransaction
class SafeTransactionViewSet(viewsets.ModelViewSet):
    queryset = SafeTransaction.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SafeTransactionPostSerializer
        return SafeTransactionGetSerializer


class DebtViewSet(viewsets.ModelViewSet):
    queryset = Debt.objects.all().order_by("-created_at")
    serializer_class = DebtSerializer
    permission_classes = [IsAuthenticated]


class DebtRepaymentViewSet(viewsets.ModelViewSet):
    queryset = DebtRepayment.objects.all().order_by("-created_at")
    serializer_class = DebtRepaymentSerializer
    permission_classes = [IsAuthenticated]
