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
    partner_name = serializers.CharField(write_only=True)
    partner_phone_number = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    safe_type_id = serializers.PrimaryKeyRelatedField(
        queryset=SafeType.objects.all(), write_only=True
    )
    is_office = serializers.BooleanField(write_only=True)
    is_person = serializers.BooleanField(write_only=True)

    class Meta:
        model = SafePartner
        fields = [
            "id",
            "partner_name",
            "partner_phone_number",
            "safe_type_id",
            "total_usd",
            "total_usdt",
            "total_iqd",
            "is_office",  # Include the new fields in the Meta
            "is_person",
        ]

    def create(self, validated_data):
        partner_name = validated_data.pop("partner_name")
        partner_phone = validated_data.pop("partner_phone_number", None)
        safe_type = validated_data.pop("safe_type_id")
        is_office = validated_data.pop("is_office")
        is_person = validated_data.pop("is_person")
        # Create or get partner
        partner, _ = Partner.objects.get_or_create(
            name=partner_name,
            defaults={"phone_number": partner_phone},
            is_office=is_office,
            is_person=is_person,
        )

        # Create SafePartner
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

    class Meta:
        model = CryptoTransaction
        fields = "__all__"


# **POST for CryptoTransaction**
class CryptoTransactionPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = CryptoTransaction
        fields = "__all__"


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
