from rest_framework import viewsets
from .models import *
from .serializers import *


# SafeType
class SafeTypeViewSet(viewsets.ModelViewSet):
    queryset = SafeType.objects.all()
    serializer_class = SafeTypeSerializer


# Partner
class PartnerViewSet(viewsets.ModelViewSet):
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer


# SafePartner
class SafePartnerViewSet(viewsets.ModelViewSet):
    queryset = SafePartner.objects.all()

    def get_serializer_class(self):
        if self.request.method in ["POST", "PUT", "PATCH"]:
            return SafePartnerCreateSerializer
        return SafePartnerSerializer


# CryptoTransaction
class CryptoTransactionViewSet(viewsets.ModelViewSet):
    queryset = CryptoTransaction.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CryptoTransactionPostSerializer
        return CryptoTransactionGetSerializer


# TransferExchange
class TransferExchangeViewSet(viewsets.ModelViewSet):
    queryset = TransferExchange.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TransferExchangePostSerializer  # Use POST if you have one
        return TransferExchangeGetSerializer


# IncomingMoney
class IncomingMoneyViewSet(viewsets.ModelViewSet):
    queryset = IncomingMoney.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return IncomingMoneyPostSerializer
        return IncomingMoneyGetSerializer


# OutgoingMoney
class OutgoingMoneyViewSet(viewsets.ModelViewSet):
    queryset = OutgoingMoney.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return OutgoingMoneyPostSerializer
        return OutgoingMoneyGetSerializer


# SafeTransaction
class SafeTransactionViewSet(viewsets.ModelViewSet):
    queryset = SafeTransaction.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SafeTransactionPostSerializer
        return SafeTransactionGetSerializer
