from django.contrib import admin
from .models import (
    Partner,
    SafeType,
    SafePartner,
    CryptoTransaction,
    Debt,
    DebtRepayment,
    TransferExchange,
    IncomingMoney,
    OutgoingMoney,
    SafeTransaction,
)


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "phone_number",
        "is_system_owner",
        "is_office",
        "is_person",
    )
    list_filter = (
        "is_system_owner",
        "is_office",
        "is_person",
    )
    search_fields = ("name", "phone_number")


@admin.register(SafeType)
class SafeTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "type")
    list_filter = ("type",)
    search_fields = ("name",)


@admin.register(SafePartner)
class SafePartnerAdmin(admin.ModelAdmin):
    list_display = (
        "partner",
        "safe_type",
        "total_usd",
        "total_usdt",
        "total_iqd",
    )
    list_filter = ("safe_type", "partner")
    search_fields = ("partner__name", "safe_type__name")


@admin.register(CryptoTransaction)
class CryptoTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "partner",
        "transaction_type",
        "usdt_amount",
        "usdt_price",
        "payment_safe",
        "crypto_safe",
        "status",
        "partner_client",
        "created_at",
    )
    list_filter = ("transaction_type", "status", "payment_safe")
    search_fields = ("partner_client__partner__name", "client_name")
    list_per_page = 25


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = (
        "debtor_name",
        "safe_partner",
        "total_amount",
        "currency",
        "remaining_amount_display",
        "is_fully_paid",
        "created_at",
    )
    list_filter = ("currency",)
    search_fields = ("debtor_name", "debtor_phone", "safe_partner__partner__name")

    def remaining_amount_display(self, obj):
        return f"{obj.remaining_amount} {obj.currency}"

    remaining_amount_display.short_description = "Remaining Amount"
    remaining_amount_display.admin_order_field = "total_amount"


@admin.register(DebtRepayment)
class DebtRepaymentAdmin(admin.ModelAdmin):
    list_display = (
        "debt",
        "amount",
        "currency",
        "safe_type",
        "created_at",
    )
    list_filter = ("currency", "safe_type")
    search_fields = ("debt__debtor_name",)


@admin.register(TransferExchange)
class TransferExchangeAdmin(admin.ModelAdmin):
    list_display = (
        "exchange_type",
        "partner",
        "usd_amount",
        "iqd_amount",
        "exchange_rate",
        "created_at",
    )
    list_filter = ("exchange_type", "partner")
    search_fields = ("partner__partner__name",)


@admin.register(IncomingMoney)
class IncomingMoneyAdmin(admin.ModelAdmin):
    list_display = (
        "from_partner",
        "to_partner",
        "money_amount",
        "currency",
        "status",
        "is_received",
        "created_at",
    )
    list_filter = ("currency", "status", "is_received")
    search_fields = (
        "from_partner__partner__name",
        "to_partner__partner__name",
        "to_name",
    )


@admin.register(OutgoingMoney)
class OutgoingMoneyAdmin(admin.ModelAdmin):
    list_display = (
        "from_partner",
        "to_partner",
        "money_amount",
        "currency",
        "status",
        "is_received",
        "created_at",
    )
    list_filter = ("currency", "status", "is_received")
    search_fields = (
        "from_partner__partner__name",
        "to_partner__partner__name",
        "from_name",
        "taker_name",
    )


@admin.register(SafeTransaction)
class SafeTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_type",
        "partner",
        "from_safepartner",
        "to_safepartner",
        "money_amount",
        "currency",
        "created_at",
    )
    list_filter = ("transaction_type", "currency")
    search_fields = (
        "partner__partner__name",
        "from_safepartner__partner__name",
        "to_safepartner__partner__name",
    )
