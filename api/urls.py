from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = DefaultRouter()
router.register(r"safe-types", SafeTypeViewSet)
router.register(r"partners", PartnerViewSet)
router.register(r"safe-partners", SafePartnerViewSet)
router.register(r"crypto-transactions", CryptoTransactionViewSet)
router.register(r"transfer-exchanges", TransferExchangeViewSet)
router.register(r"incoming-money", IncomingMoneyViewSet)
router.register(r"outgoing-money", OutgoingMoneyViewSet)
router.register(r"safe-transactions", SafeTransactionViewSet)
router.register(r"debts", DebtViewSet)
router.register(r"debt-repayments", DebtRepaymentViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
