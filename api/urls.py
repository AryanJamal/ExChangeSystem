from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r"safe-types", SafeTypeViewSet)
router.register(r"partners", PartnerViewSet)
router.register(r"safe-partners", SafePartnerViewSet)
router.register(r"crypto-transactions", CryptoTransactionViewSet)
router.register(r"transfer-exchanges", TransferExchangeViewSet)
router.register(r"incoming-money", IncomingMoneyViewSet)
router.register(r"outgoing-money", OutgoingMoneyViewSet)
router.register(r"safe-transactions", SafeTransactionViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
