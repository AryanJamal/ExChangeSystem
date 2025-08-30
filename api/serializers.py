from rest_framework import serializers
from .models import *


# **GET/POST for SafeType**
class SafeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafeType
        fields = ["id", "name", "type"]


# **GET/POST for Partner**
class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = [
            "id",
            "name",
            "phone_number",
            "is_system_owner",
            "is_office",
            "is_person",
        ]


# **Get for SafePartner**
class SafePartnerSerializer(serializers.ModelSerializer):
    partner = PartnerSerializer(read_only=True)
    safe_type = SafeTypeSerializer(read_only=True)

    class Meta:
        model = SafePartner
        fields = [
            "id",
            "partner",
            "safe_type",
            "total_usd",
            "total_usdt",
            "total_iqd",
        ]


# **POST for SafePartner**


class SafePartnerCreateSerializer(serializers.ModelSerializer):
    partner_id = serializers.PrimaryKeyRelatedField(
        queryset=Partner.objects.all(), write_only=True
    )
    safe_type_id = serializers.PrimaryKeyRelatedField(
        queryset=SafeType.objects.all(), write_only=True
    )

    class Meta:
        model = SafePartner
        fields = [
            "id",
            "partner_id",
            "safe_type_id",
            "total_usd",
            "total_usdt",
            "total_iqd",
        ]

    def create(self, validated_data):
        partner = validated_data.pop("partner_id")
        safe_type = validated_data.pop("safe_type_id")

        # Create SafePartner with the existing partner
        safe_partner = SafePartner.objects.create(
            partner=partner, safe_type=safe_type, **validated_data
        )
        return safe_partner

    def update(self, instance, validated_data):
        # Update Partner
        partner_name = validated_data.pop("partner_name", None)
        partner_phone = validated_data.pop("partner_phone_number", None)
        safe_type = validated_data.pop("safe_type_id", None)

        if partner_name:
            instance.partner.name = partner_name
        if partner_phone is not None:
            instance.partner.phone_number = partner_phone
        instance.partner.save()

        if safe_type:
            instance.safe_type = safe_type

        return super().update(instance, validated_data)


# **GET for CryptoTransaction**
class CryptoTransactionGetSerializer(serializers.ModelSerializer):
    partner = SafePartnerSerializer(read_only=True)
    partner_client = PartnerSerializer(read_only=True)

    class Meta:
        model = CryptoTransaction
        fields = "__all__"


# **POST for CryptoTransaction**
class CryptoTransactionPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = CryptoTransaction
        fields = "__all__"


class CryptoTransactionStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CryptoTransaction
        fields = ["status", "bonus"]


# **GET/POST for TransferExchange**
class TransferExchangeGetSerializer(serializers.ModelSerializer):
    partner = SafePartnerSerializer()

    class Meta:
        model = TransferExchange
        fields = "__all__"


class TransferExchangePostSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransferExchange
        fields = "__all__"


# **GET for IncomingMoney**
class IncomingMoneyGetSerializer(serializers.ModelSerializer):
    from_partner = SafePartnerSerializer(read_only=True)
    to_partner = SafePartnerSerializer(read_only=True)

    class Meta:
        model = IncomingMoney
        fields = "__all__"


# **POST for IncomingMoney**
class IncomingMoneyPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncomingMoney
        fields = [
            "from_partner",
            "money_amount",
            "currency",
            "to_partner",
            "to_name",
            "to_number",
            "status",
            "my_bonus",
            "partner_bonus",
            "bonus_currency",
            "note",
        ]


# new serializer for the status update
class IncomingMoneyStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncomingMoney
        fields = ["status", "my_bonus", "partner_bonus"]


# **GET for OutgoingMoney**
class OutgoingMoneyGetSerializer(serializers.ModelSerializer):
    from_partner = SafePartnerSerializer(read_only=True)
    to_partner = SafePartnerSerializer(read_only=True)

    class Meta:
        model = OutgoingMoney
        fields = "__all__"


# **POST for IncomingMoney**
class OutgoingMoneyPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutgoingMoney
        fields = [
            "from_partner",
            "money_amount",
            "currency",
            "to_partner",
            "from_name",
            "from_number",
            "status",
            "taker_name",
            "my_bonus",
            "partner_bonus",
            "bonus_currency",
            "note",
        ]


class OutgoingMoneyStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutgoingMoney
        fields = ["status", "my_bonus", "partner_bonus"]


# **GET for SafeTransaction**
class SafeTransactionGetSerializer(serializers.ModelSerializer):
    partner = SafePartnerSerializer(read_only=True)

    class Meta:
        model = SafeTransaction
        fields = "__all__"


# **POST for SafeTransaction**
class SafeTransactionPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafeTransaction
        fields = [
            "partner",
            "transaction_type",
            "money_amount",
            "currency",
            "note",
        ]


# **GET/POST for Debts**
class DebtRepaymentSerializer(serializers.ModelSerializer):
    debt_id = serializers.PrimaryKeyRelatedField(
        queryset=Debt.objects.all(), source="debt", write_only=True
    )

    class Meta:
        model = DebtRepayment
        fields = ["id", "debt_id", "amount", "created_at"]


class DebtSerializer(serializers.ModelSerializer):
    debt_safe = SafeTypeSerializer(read_only=True)
    debt_safe_id = serializers.PrimaryKeyRelatedField(
        queryset=SafeType.objects.all(), source="debt_safe", write_only=True
    )

    repayments = DebtRepaymentSerializer(many=True, read_only=True)

    amount_repaid = serializers.DecimalField(
        max_digits=20, decimal_places=2, read_only=True
    )
    remaining_amount = serializers.DecimalField(
        max_digits=20, decimal_places=2, read_only=True
    )
    is_fully_paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Debt
        fields = [
            "id",
            "debt_safe",
            "debt_safe_id",
            "debtor_name",
            "debtor_phone",
            "total_amount",
            "currency",
            "note",
            "amount_repaid",
            "remaining_amount",
            "is_fully_paid",
            "repayments",
            "created_at",
            "updated_at",
        ]
