from decimal import Decimal
from django.forms import DecimalField
from rest_framework import viewsets
from .models import *
from .serializers import *
from django.utils import timezone
from django.db.models import Q
from datetime import date, timedelta
from .pagination import TenPerPagePagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Sum, F, DecimalField, Case, When
from rest_framework.response import Response
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import action
from datetime import datetime

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
    queryset = CryptoTransaction.objects.all().order_by("-created_at")
    pagination_class = TenPerPagePagination
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CryptoTransactionPostSerializer
        if self.request.method in ["PUT", "PATCH"]:
            return CryptoTransactionStatusUpdateSerializer
        return CryptoTransactionGetSerializer

    def get_queryset(self):
        queryset = super().get_queryset()  # Start with the base queryset (all objects)

        if self.action in ["retrieve", "update", "partial_update", "destroy"]:
            return queryset.order_by("-created_at")
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
    queryset = TransferExchange.objects.all().order_by("-created_at")
    pagination_class = TenPerPagePagination
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TransferExchangePostSerializer  # Use POST if you have one
        return TransferExchangeGetSerializer


# IncomingMoney
class IncomingMoneyViewSet(viewsets.ModelViewSet):
    queryset = IncomingMoney.objects.all().order_by("-created_at")
    pagination_class = TenPerPagePagination
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return IncomingMoneyPostSerializer
        if self.request.method in ["PATCH", "PUT"]:
            return IncomingMoneyStatusUpdateSerializer
        return IncomingMoneyGetSerializer

    def get_queryset(self):
        queryset = IncomingMoney.objects.all().order_by("-created_at")
        query_params = self.request.query_params

        if self.action in ["retrieve", "update", "partial_update", "destroy"]:
            return queryset.order_by("-created_at")
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
    queryset = OutgoingMoney.objects.all().order_by("-created_at")
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return OutgoingMoneyPostSerializer
        if self.request.method in ["PATCH", "PUT"]:
            return OutgoingMoneyStatusUpdateSerializer
        return OutgoingMoneyGetSerializer

    def get_queryset(self):

        queryset = OutgoingMoney.objects.all().order_by("-created_at")

        # Get query parameters from the request
        query_params = self.request.query_params
        if self.action in ["retrieve", "update", "partial_update", "destroy"]:
            return queryset.order_by("-created_at")

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
                | Q(partner_client__partner__name__icontains=search_query)
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
    queryset = SafeTransaction.objects.all().order_by("-created_at")
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


# ** REPORT


def calculate_bonus(queryset, date_field=None, start=None, end=None):
    """
    Helper to calculate total bonus, optionally filtered by date range.
    """
    if start and end:
        queryset = queryset.filter(
            **{f"{date_field}__gte": start, f"{date_field}__lte": end}
        )

    crypto_bonus = (
        queryset[0]
        .annotate(
            adjusted_bonus=Case(
                When(partner__isnull=False, then=F("bonus") / Decimal("2")),
                default=F("bonus"),
                output_field=DecimalField(max_digits=20, decimal_places=2),
            )
        )
        .values("bonus_currency")
        .annotate(total=Sum("adjusted_bonus"))
        if queryset
        else []
    )

    transfer_bonus = (
        queryset[1].values("bonus_currency").annotate(total=Sum("my_bonus"))
        if queryset
        else []
    )
    incoming_bonus = (
        queryset[2].values("bonus_currency").annotate(total=Sum("my_bonus"))
        if queryset
        else []
    )
    outgoing_bonus = (
        queryset[3].values("bonus_currency").annotate(total=Sum("my_bonus"))
        if queryset
        else []
    )

    bonus_totals = {}
    for entry in (
        list(crypto_bonus)
        + list(transfer_bonus)
        + list(incoming_bonus)
        + list(outgoing_bonus)
    ):
        currency = entry["bonus_currency"]
        total = entry["total"] or 0
        bonus_totals[currency] = bonus_totals.get(currency, 0) + total

    return bonus_totals


class TodayBonusViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        today = timezone.now().date()
        start = timezone.datetime.combine(
            today, timezone.datetime.min.time(), tzinfo=timezone.get_current_timezone()
        )
        end = timezone.datetime.combine(
            today, timezone.datetime.max.time(), tzinfo=timezone.get_current_timezone()
        )

        crypto_qs = CryptoTransaction.objects.filter(
            created_at__gte=start, created_at__lte=end
        )
        transfer_qs = TransferExchange.objects.filter(
            created_at__gte=start, created_at__lte=end
        )
        incoming_qs = IncomingMoney.objects.filter(
            created_at__gte=start, created_at__lte=end
        )
        outgoing_qs = OutgoingMoney.objects.filter(
            created_at__gte=start, created_at__lte=end
        )

        bonuses = calculate_bonus([crypto_qs, transfer_qs, incoming_qs, outgoing_qs])
        return Response(bonuses)


class MonthBonusViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        now = timezone.now()
        start = timezone.datetime(
            now.year, now.month, 1, tzinfo=timezone.get_current_timezone()
        )
        end = timezone.now()  # now for up-to-current moment

        crypto_qs = CryptoTransaction.objects.filter(
            created_at__gte=start, created_at__lte=end
        )
        transfer_qs = TransferExchange.objects.filter(
            created_at__gte=start, created_at__lte=end
        )
        incoming_qs = IncomingMoney.objects.filter(
            created_at__gte=start, created_at__lte=end
        )
        outgoing_qs = OutgoingMoney.objects.filter(
            created_at__gte=start, created_at__lte=end
        )

        bonuses = calculate_bonus([crypto_qs, transfer_qs, incoming_qs, outgoing_qs])
        return Response(bonuses)


class PartnerReportViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["get"], url_path="report")
    def report(self, request, pk=None):
        start = request.query_params.get("start")
        end = request.query_params.get("end")

        try:
            partner = Partner.objects.get(id=pk)
        except Partner.DoesNotExist:
            return Response({"error": "Partner not found"}, status=404)

        date_filter = {}
        # ... (Your date filtering logic remains the same)
        if start:
            try:
                date_filter["created_at__gte"] = parse_datetime(
                    start
                ) or datetime.fromisoformat(start)
            except:
                pass
        if end:
            try:
                end_date = parse_datetime(end) or datetime.fromisoformat(end)
                date_filter["created_at__lte"] = end_date + timedelta(
                    days=1
                ) or datetime.fromisoformat(end)
            except:
                pass

        partner_name = partner.name

        # ✅ Crypto Transactions
        # The key change is here: partner_client__partner__name
        crypto_qs = (
            CryptoTransaction.objects.filter(
                Q(partner__partner__name=partner_name),
                **date_filter,
            )
            .values()
            .order_by("-created_at")
        )

        # ✅ Incoming Money
        incoming_qs = (
            IncomingMoney.objects.filter(
                Q(to_partner__partner__name=partner_name),
                **date_filter,
            )
            .values()
            .order_by("-created_at")
        )

        # ✅ Outgoing Money
        outgoing_qs = OutgoingMoney.objects.filter(
            Q(from_partner__partner__name=partner_name),
            **date_filter,
        ).values()

        return Response(
            {
                "partner": partner.name,
                "crypto_transactions": list(crypto_qs),
                "incoming_money": list(incoming_qs),
                "outgoing_money": list(outgoing_qs),
            }
        )
