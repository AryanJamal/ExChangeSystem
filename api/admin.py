from django.contrib import admin
from .models import *


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
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
    list_display = (
        "name",
        "type",
    )
    list_filter = ("type",)
    search_fields = ("name",)


@admin.register(SafePartner)
class SafePartnerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "partner",
        "safe_type",
        "total_usd",
        "total_usdt",
        "total_iqd",
    )
    list_filter = ("safe_type",)
    search_fields = ("partner__name", "safe_type__name")


@admin.register(CryptoTransaction)
class CryptoTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_type",
        "partner",
        "usdt_amount",
        "usdt_price",
        "status",
        "created_at",
    )
    list_filter = (
        "transaction_type",
        "status",
        "currency",
        "crypto_safe",
    )
    search_fields = (
        "partner__partner__name",
        "client_name",
        "partner_client__partner__name",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(TransferExchange)
class TransferExchangeAdmin(admin.ModelAdmin):
    list_display = (
        "partner",
        "exchange_type",
        "usd_amount",
        "iqd_amount",
        "exchange_rate",
        "created_at",
    )
    list_filter = ("exchange_type",)
    search_fields = ("partner__partner__name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(IncomingMoney)
class IncomingMoneyAdmin(admin.ModelAdmin):
    list_display = (
        "from_partner",
        "to_partner",
        "money_amount",
        "currency",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("from_partner__partner__name", "to_partner__partner__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(OutgoingMoney)
class OutgoingMoneyAdmin(admin.ModelAdmin):
    list_display = (
        "from_partner",
        "to_partner",
        "money_amount",
        "currency",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("from_partner__partner__name", "to_partner__partner__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SafeTransaction)
class SafeTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "partner",
        "transaction_type",
        "money_amount",
        "currency",
        "created_at",
    )
    list_filter = ("transaction_type",)
    search_fields = ("partner__partner__name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = (
        "debtor_name",
        "debtor_phone",
        "safe_partner",
        "debt_safe",
        "total_amount",
        "currency",
        "amount_repaid",
        "remaining_amount",
        "is_fully_paid",
        "created_at",
    )
    list_filter = (
        "currency",
        "created_at",
    )
    search_fields = ("debtor_name", "debtor_phone", "note")
    readonly_fields = ("amount_repaid", "remaining_amount", "is_fully_paid")


@admin.register(DebtRepayment)
class DebtRepaymentAdmin(admin.ModelAdmin):
    list_display = ("debt", "amount", "safe_type", "currency", "created_at")
    list_filter = ("currency", "created_at")
    search_fields = ("debt__debtor_name",)
