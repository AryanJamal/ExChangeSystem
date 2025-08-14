from django.db import models


# ------------------------------------
# 1. Partner
# ------------------------------------
class Partner(models.Model):
    name = models.CharField(max_length=100, unique=True)
    phone_number = models.BigIntegerField(default=0, null=True)
    is_system_owner = models.BooleanField(default=False)
    is_office = models.BooleanField(default=False)
    is_person = models.BooleanField(default=False)

    def __str__(self):
        return self.name


# ------------------------------------
# 2. SafeType
# ------------------------------------
class SafeType(models.Model):
    TYPES_CHOICES = [
        ("Crypto", "Crypto"),
        ("Physical", "Physical"),
    ]
    name = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=10, choices=TYPES_CHOICES)

    def __str__(self):
        return f"Safe - {self.name}"


# ------------------------------------
# 3. Safe Balance per Partner
# ------------------------------------
class SafePartner(models.Model):
    partner = models.ForeignKey(
        Partner, on_delete=models.PROTECT, related_name="safe_balances"
    )
    safe_type = models.ForeignKey(SafeType, on_delete=models.PROTECT)
    total_usd = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_usdt = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_iqd = models.BigIntegerField(default=0)

    class Meta:
        unique_together = ("partner", "safe_type")

    def __str__(self):
        return f"Safe - {self.safe_type} for {self.partner.name}"


# ------------------------------------
# 4. Crypto Transactions
# ------------------------------------
class CryptoTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ("Buy", "Buy"),
        ("Sell", "Sell"),
    ]
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    ]
    CURRENCY_CHOICES = [
        ("USDT", "USDT"),
        ("USD", "USD"),
        ("IQD", "IQD"),
    ]

    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPE_CHOICES,
    )
    partner = models.ForeignKey(
        SafePartner, on_delete=models.PROTECT, null=True, blank=True
    )
    usdt_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
    )
    usdt_price = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
    )
    crypto_safe = models.ForeignKey(
        SafeType,
        on_delete=models.PROTECT,
        related_name="crypto_wallet_safe",
    )
    bonus = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    bonus_currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    payment_safe = models.ForeignKey(
        SafeType,
        on_delete=models.PROTECT,
        related_name="crypto_payment_safe",
    )
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES)
    client_name = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "transaction_type"]),
            models.Index(fields=["partner", "status"]),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


# ------------------------------------
# 3. Transfer Exchange (Currency Conversion in Safe)
# ------------------------------------
class TransferExchange(models.Model):
    EXCHANGE_CHOICES = [
        ("USD_TO_IQD", "USD to IQD"),
        ("IQD_TO_USD", "IQD to USD"),
    ]
    partner = models.ForeignKey(
        SafePartner,
        on_delete=models.PROTECT,
    )
    exchange_type = models.CharField(max_length=10, choices=EXCHANGE_CHOICES)
    usd_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    iqd_amount = models.BigIntegerField(default=0)
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# ------------------------------------
# 4. Incoming Money
# ------------------------------------
class IncomingMoney(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Completed", "Completed"),
    ]
    CURRENCY_CHOICES = [
        ("USD", "USD"),
        ("IQD", "IQD"),
    ]
    from_partner = models.ForeignKey(
        SafePartner,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incoming_from",
    )
    money_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default="USD")
    to_partner = models.ForeignKey(
        SafePartner,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incoming_to",
    )
    to_name = models.CharField(max_length=100, blank=True, null=True)
    to_number = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    my_bonus = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    partner_bonus = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    bonus_currency = models.CharField(
        max_length=5, choices=CURRENCY_CHOICES, default="USD"
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# ------------------------------------
# 5. Outgoing Money
# ------------------------------------
class OutgoingMoney(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Completed", "Completed"),
    ]
    CURRENCY_CHOICES = [
        ("USD", "USD"),
        ("IQD", "IQD"),
    ]
    to_partner = models.ForeignKey(
        SafePartner,
        on_delete=models.PROTECT,
        related_name="outgoing_to",
    )
    money_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default="USD")
    from_partner = models.ForeignKey(
        SafePartner,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="outgoing_from",
    )
    from_name = models.CharField(max_length=100, blank=True, null=True)
    from_number = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    taker_name = models.CharField(max_length=100)
    my_bonus = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    partner_bonus = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    bonus_currency = models.CharField(
        max_length=5, choices=CURRENCY_CHOICES, default="USD"
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SafeTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ("ADD", "Add (Deposit)"),
        ("REMOVE", "Remove (Withdrawal)"),
    ]
    CURRENCY_CHOICES = [
        ("USDT", "USDT"),
        ("USD", "USD"),
        ("IQD", "IQD"),
    ]
    partner = models.ForeignKey(SafePartner, on_delete=models.PROTECT)
    transaction_type = models.CharField(max_length=6, choices=TRANSACTION_TYPE_CHOICES)
    money_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default="USD")
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.transaction_type.capitalize()} by {self.partner.partner.name}"
