from django.db import models

from decimal import Decimal


# ------------------------------------
# 1. Partner
# ------------------------------------
class Partner(models.Model):
    name = models.CharField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
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
        SafePartner,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="crypto_partner",
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
    # it sold to stranger or maybe partners
    client_name = models.CharField(max_length=100, blank=True, null=True)
    partner_client = models.ForeignKey(
        SafePartner,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="crypto_client",
    )

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
# Debt Model
# ------------------------------------
class Debt(models.Model):
    CURRENCY_CHOICES = [
        ("USDT", "USDT"),
        ("USD", "USD"),
        ("IQD", "IQD"),
    ]
    debt_safe = models.ForeignKey(
        SafeType,
        on_delete=models.PROTECT,
        related_name="debt_safe",
    )
    safe_partner = models.ForeignKey(  # partner who owes money
        "SafePartner",
        on_delete=models.PROTECT,
        related_name="debts",
        null=True,
        blank=True,
    )
    debtor_name = models.CharField(max_length=100, null=True, blank=True)
    debtor_phone = models.CharField(max_length=20, blank=True, null=True)

    total_amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default="USD")

    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def amount_repaid(self):
        """Sum repayments converted into the debt's currency."""
        total = Decimal("0.00")
        for repayment in self.repayments.all():
            total += repayment.converted_amount(self.currency)
        return total

    @property
    def remaining_amount(self):
        return self.total_amount - self.amount_repaid

    @property
    def is_fully_paid(self):
        return self.remaining_amount <= 0

    def __str__(self):
        return f"{self.debtor_name} owes {self.remaining_amount} {self.currency}"


class DebtRepayment(models.Model):
    CURRENCY_CHOICES = [
        ("USDT", "USDT"),
        ("USD", "USD"),
        ("IQD", "IQD"),
    ]
    debt = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name="repayments")
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    safe_type = models.ForeignKey(
        SafeType,
        on_delete=models.PROTECT,
        related_name="debt_safe_repayments",
        null=True,
    )
    currency = models.CharField(
        max_length=5,
        choices=CURRENCY_CHOICES,
        default="USD",
    )
    # 👇 New field: conversion rate relative to the debt’s currency
    conversion_rate = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        default=1.0,
        help_text="Rate to convert repayment currency to debt currency",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def converted_amount(self, target_currency=None):
        """
        Convert repayment amount into target currency.
        Currently assumes conversion_rate already set correctly.
        """
        if self.debt.currency == "USD":
            if self.currency == "IQD":
                return self.amount / self.conversion_rate
        if self.debt.currency == "IQD":
            if self.currency == "USD":
                return self.amount * self.conversion_rate
        return self.amount * self.conversion_rate

    def __str__(self):
        return f"Repayment {self.amount} {self.currency} for {self.debt.debtor_name}"


# ------------------------------------
# 3. Transfer Exchange (Currency Conversion in Safe)
# ------------------------------------
class TransferExchange(models.Model):
    EXCHANGE_CHOICES = [
        ("USD_TO_IQD", "USD to IQD"),
        ("IQD_TO_USD", "IQD to USD"),
    ]
    CURRENCY_CHOICES = [
        ("USD", "USD"),
        ("IQD", "IQD"),
    ]
    partner = models.ForeignKey(
        SafePartner,
        on_delete=models.PROTECT,
    )
    exchange_type = models.CharField(max_length=10, choices=EXCHANGE_CHOICES)
    usd_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    iqd_amount = models.BigIntegerField(default=0)
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=2)
    my_bonus = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    bonus_currency = models.CharField(
        max_length=5, choices=CURRENCY_CHOICES, default="USD"
    )
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
    is_received = models.BooleanField(default=False)
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
    is_received = models.BooleanField(default=False)
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
        ("EXPENSE", "Expense"),
        ("TRANSFER", "Transfer"),  # Added for safe-to-safe transfers
    ]
    CURRENCY_CHOICES = [
        ("USDT", "USDT"),
        ("USD", "USD"),
        ("IQD", "IQD"),
    ]

    # Old field, now can be null
    partner = models.ForeignKey(
        SafePartner,
        on_delete=models.PROTECT,
        null=True,  # Allows this field to be null for 'TRANSFER' transactions
        blank=True,
        related_name="transactions",  # Good practice to specify related_name
    )

    # New fields for 'TRANSFER' transactions
    from_safepartner = models.ForeignKey(
        SafePartner,
        on_delete=models.PROTECT,
        null=True,  # This is only used for 'TRANSFER' type
        blank=True,
        related_name="sent_transfers",
    )
    to_safepartner = models.ForeignKey(
        SafePartner,
        on_delete=models.PROTECT,
        null=True,  # This is only used for 'TRANSFER' type
        blank=True,
        related_name="received_transfers",
    )

    transaction_type = models.CharField(
        max_length=8, choices=TRANSACTION_TYPE_CHOICES
    )  # Increased max_length
    money_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default="USD")
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.transaction_type == "TRANSFER":
            return f"Transfer from {self.from_safepartner.partner.name} to {self.to_safepartner.partner.name}"
        else:
            return (
                f"{self.get_transaction_type_display()} by {self.partner.partner.name}"
            )
