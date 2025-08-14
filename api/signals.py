from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from django.db import transaction
from decimal import Decimal
from .models import (
    CryptoTransaction,
    Partner,
    SafePartner,
    IncomingMoney,
    OutgoingMoney,
    SafeTransaction,
    TransferExchange,
)


# *************************
# Exchange Money
# *************************


@receiver(post_save, sender=TransferExchange)
def transfer_exchange_post_save(sender, instance, created, **kwargs):
    """
    Handle currency exchange when TransferExchange is created
    """
    if not created:
        # Only process new exchanges to avoid duplicate processing
        return

    handle_currency_exchange(instance)


def handle_currency_exchange(instance):
    """
    Exchange currency between USD and IQD for the partner
    """
    with transaction.atomic():
        partner = instance.partner

        if instance.exchange_type == "USD_TO_IQD":
            # Convert USD to IQD
            # Subtract USD from partner's balance
            partner.total_usd -= Decimal(instance.usd_amount)
            # Add IQD to partner's balance
            partner.total_iqd += instance.iqd_amount

        elif instance.exchange_type == "IQD_TO_USD":
            # Convert IQD to USD
            # Subtract IQD from partner's balance
            partner.total_iqd -= instance.iqd_amount
            # Add USD to partner's balance
            partner.total_usd += Decimal(instance.usd_amount)

        # Save the updated partner balance
        partner.save()


# *************************
# Crypto
# *************************
@receiver(pre_save, sender=CryptoTransaction)
def crypto_transaction_pre_save(sender, instance, **kwargs):
    """
    Store the old status before saving to determine if we need to apply balances
    """
    instance._old_status = None
    if instance.pk:  # Existing record
        try:
            old_instance = CryptoTransaction.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except CryptoTransaction.DoesNotExist:
            pass


@receiver(post_save, sender=CryptoTransaction)
def crypto_transaction_post_save(sender, instance, created, **kwargs):
    """
    Handle balance updates after the CryptoTransaction is saved
    """
    # Determine if this is a status change from Pending -> Completed
    apply_balances = False

    if created:  # New record
        if instance.status == "Completed":
            apply_balances = True
    else:  # Existing record
        old_status = getattr(instance, "_old_status", None)
        if old_status == "Pending" and instance.status == "Completed":
            apply_balances = True

    if not apply_balances:
        return

    try:
        owner = Partner.objects.get(is_system_owner=True)
        payment_safe = SafePartner.objects.get(
            partner=owner, safe_type=instance.payment_safe
        )
        crypto_safe = SafePartner.objects.get(
            partner=owner, safe_type=instance.crypto_safe
        )
    except (Partner.DoesNotExist, SafePartner.DoesNotExist):
        # A completed transaction requires the system owner and their safes to exist
        return

    with transaction.atomic():
        # --- Handle USDT movement ---
        if instance.transaction_type == "Buy":
            crypto_safe.total_usdt += Decimal(instance.usdt_amount)
        elif instance.transaction_type == "Sell":
            crypto_safe.total_usdt -= Decimal(instance.usdt_amount)

        # --- Handle fiat movement ---
        if instance.currency == "USD":
            if instance.transaction_type == "Buy":
                payment_safe.total_usd -= Decimal(instance.usdt_price)
            elif instance.transaction_type == "Sell":
                payment_safe.total_usd += Decimal(instance.usdt_price)
        elif instance.currency == "IQD":
            if instance.transaction_type == "Buy":
                payment_safe.total_iqd -= Decimal(instance.usdt_price)
            elif instance.transaction_type == "Sell":
                payment_safe.total_iqd += Decimal(instance.usdt_price)

        # --- Handle bonus distribution ---
        if instance.partner:
            partner_bonus = instance.bonus / Decimal("2")
            owner_bonus = instance.bonus - partner_bonus

            # Partner bonus
            if instance.bonus_currency == "USDT":
                instance.partner.total_usdt += partner_bonus
            elif instance.bonus_currency == "USD":
                instance.partner.total_usd += partner_bonus
            elif instance.bonus_currency == "IQD":
                instance.partner.total_iqd += partner_bonus
            instance.partner.save()

            # Owner bonus
            if instance.bonus_currency == "USDT":
                crypto_safe.total_usdt += owner_bonus
            elif instance.bonus_currency == "USD":
                payment_safe.total_usd += owner_bonus
            elif instance.bonus_currency == "IQD":
                payment_safe.total_iqd += owner_bonus
        else:
            owner_bonus = instance.bonus
            if instance.bonus_currency == "USDT":
                crypto_safe.total_usdt += owner_bonus
            elif instance.bonus_currency == "USD":
                payment_safe.total_usd += owner_bonus
            elif instance.bonus_currency == "IQD":
                payment_safe.total_iqd += owner_bonus

        # Save updated safe balances
        crypto_safe.save()
        payment_safe.save()


# *************************
# Incoming Money
# *************************
def adjust_safe_balance(safe_partner, amount, currency, add=True):
    """Adjust a SafePartner's balance for a given currency."""
    if not safe_partner or amount == 0:
        return
    field = "total_usd" if currency == "USD" else "total_iqd"
    current_value = getattr(safe_partner, field, Decimal("0.00"))
    new_value = current_value + amount if add else current_value - amount
    setattr(safe_partner, field, new_value)
    safe_partner.save(update_fields=[field])


@receiver(pre_save, sender=IncomingMoney)
def incomingmoney_pre_save(sender, instance, **kwargs):
    if not instance.pk:
        return  # New record → nothing to reverse yet

    old = IncomingMoney.objects.get(pk=instance.pk)

    # --- Reverse from_partner deduction if money/currency/partner changed ---
    if (
        old.money_amount != instance.money_amount
        or old.currency != instance.currency
        or old.from_partner_id != instance.from_partner_id
    ):
        adjust_safe_balance(old.from_partner, old.money_amount, old.currency, add=True)

    # --- Reverse bonuses & to_partner if old status was Completed ---
    if old.status == "Completed":
        owner = Partner.objects.get(is_system_owner=True)
        owner_safe = SafePartner.objects.get(partner=owner, safe_type__name="قاسە")
        adjust_safe_balance(owner_safe, old.my_bonus, old.bonus_currency, add=False)
        adjust_safe_balance(
            old.from_partner, old.partner_bonus, old.bonus_currency, add=False
        )

        # Reverse to_partner addition
        if old.to_partner:
            adjust_safe_balance(
                old.to_partner, old.money_amount, old.currency, add=False
            )
            # Reverse my_bonus subtraction from to_partner
            adjust_safe_balance(
                old.to_partner, old.my_bonus, old.bonus_currency, add=True
            )
            adjust_safe_balance(
                old.to_partner, old.partner_bonus, old.bonus_currency, add=True
            )


@receiver(post_save, sender=IncomingMoney)
def incomingmoney_post_save(sender, instance, created, **kwargs):
    with transaction.atomic():
        # --- Handle money_amount subtraction ---
        if created:
            adjust_safe_balance(
                instance.from_partner,
                instance.money_amount,
                instance.currency,
                add=False,
            )
        else:
            old = IncomingMoney.objects.get(pk=instance.pk)
            if (
                old.money_amount != instance.money_amount
                or old.currency != instance.currency
                or old.from_partner_id != instance.from_partner_id
            ):
                adjust_safe_balance(
                    instance.from_partner,
                    instance.money_amount,
                    instance.currency,
                    add=False,
                )

        # --- Apply bonuses & to_partner changes only if Completed ---
        if instance.status == "Completed":
            owner = Partner.objects.get(is_system_owner=True)
            owner_safe = SafePartner.objects.get(partner=owner, safe_type__name="قاسە")

            adjust_safe_balance(
                owner_safe, instance.my_bonus, instance.bonus_currency, add=True
            )
            adjust_safe_balance(
                instance.from_partner,
                instance.partner_bonus,
                instance.bonus_currency,
                add=True,
            )

            if instance.to_partner:
                adjust_safe_balance(
                    instance.to_partner,
                    instance.money_amount,
                    instance.currency,
                    add=True,
                )
                # Subtract my_bonus from to_partner
                adjust_safe_balance(
                    instance.to_partner,
                    instance.my_bonus,
                    instance.bonus_currency,
                    add=False,
                )
                adjust_safe_balance(
                    instance.to_partner,
                    instance.partner_bonus,
                    instance.bonus_currency,
                    add=False,
                )


@receiver(pre_delete, sender=IncomingMoney)
def incomingmoney_pre_delete(sender, instance, **kwargs):
    with transaction.atomic():
        # Reverse from_partner deduction
        adjust_safe_balance(
            instance.from_partner, instance.money_amount, instance.currency, add=True
        )

        if instance.status == "Completed":
            owner = Partner.objects.get(is_system_owner=True)
            owner_safe = SafePartner.objects.get(partner=owner, safe_type__name="قاسە")
            adjust_safe_balance(
                owner_safe, instance.my_bonus, instance.bonus_currency, add=False
            )

            adjust_safe_balance(
                instance.from_partner,
                instance.partner_bonus,
                instance.bonus_currency,
                add=False,
            )

            if instance.to_partner:
                adjust_safe_balance(
                    instance.to_partner,
                    instance.money_amount,
                    instance.currency,
                    add=False,
                )
                # Reverse my_bonus subtraction from to_partner
                adjust_safe_balance(
                    instance.to_partner,
                    instance.my_bonus,
                    instance.bonus_currency,
                    add=True,
                )
                adjust_safe_balance(
                    instance.to_partner,
                    instance.partner_bonus,
                    instance.bonus_currency,
                    add=True,
                )


# *************************
# Outgoing Money
# *************************
def adjust_safe_balance(safe_partner, amount, currency, add=True):
    """Adjust a SafePartner's balance for a given currency."""
    if not safe_partner or amount == 0:
        return
    field = "total_usd" if currency == "USD" else "total_iqd"
    current_value = getattr(safe_partner, field, Decimal("0.00"))
    new_value = current_value + amount if add else current_value - amount
    setattr(safe_partner, field, new_value)
    safe_partner.save(update_fields=[field])


@receiver(pre_save, sender=OutgoingMoney)
def outgoingmoney_pre_save(sender, instance, **kwargs):
    if not instance.pk:
        return  # New record → nothing to reverse yet

    old = OutgoingMoney.objects.get(pk=instance.pk)

    # --- Reverse to_partner addition if money/currency/partner changed ---
    if (
        old.money_amount != instance.money_amount
        or old.currency != instance.currency
        or old.to_partner_id != instance.to_partner_id
    ):
        adjust_safe_balance(old.to_partner, old.money_amount, old.currency, add=False)

    # --- Reverse bonuses & from_partner if old status was Completed ---
    if old.status == "Completed":
        owner = Partner.objects.get(is_system_owner=True)
        owner_safe = SafePartner.objects.get(partner=owner, safe_type__name="قاسە")
        adjust_safe_balance(owner_safe, old.my_bonus, old.bonus_currency, add=False)
        adjust_safe_balance(
            old.to_partner, old.partner_bonus, old.bonus_currency, add=False
        )

        # Reverse from_partner subtraction
        if old.from_partner:
            adjust_safe_balance(
                old.from_partner, old.money_amount, old.currency, add=True
            )


@receiver(post_save, sender=OutgoingMoney)
def outgoingmoney_post_save(sender, instance, created, **kwargs):
    with transaction.atomic():
        # --- Handle money_amount addition to to_partner ---
        if created:
            adjust_safe_balance(
                instance.to_partner,
                instance.money_amount,
                instance.currency,
                add=True,
            )
        else:
            old = OutgoingMoney.objects.get(pk=instance.pk)
            if (
                old.money_amount != instance.money_amount
                or old.currency != instance.currency
                or old.to_partner_id != instance.to_partner_id
            ):
                adjust_safe_balance(
                    instance.to_partner,
                    instance.money_amount,
                    instance.currency,
                    add=True,
                )

        # --- Apply bonuses & from_partner changes only if Completed ---
        if instance.status == "Completed":
            owner = Partner.objects.get(is_system_owner=True)
            owner_safe = SafePartner.objects.get(partner=owner, safe_type__name="قاسە")

            adjust_safe_balance(
                owner_safe, instance.my_bonus, instance.bonus_currency, add=True
            )
            adjust_safe_balance(
                instance.to_partner,
                instance.partner_bonus,
                instance.bonus_currency,
                add=True,
            )

            if instance.from_partner:
                adjust_safe_balance(
                    instance.from_partner,
                    instance.money_amount,
                    instance.currency,
                    add=False,
                )


@receiver(pre_delete, sender=OutgoingMoney)
def outgoingmoney_pre_delete(sender, instance, **kwargs):
    with transaction.atomic():
        # Reverse to_partner addition
        adjust_safe_balance(
            instance.to_partner, instance.money_amount, instance.currency, add=False
        )

        if instance.status == "Completed":
            owner = Partner.objects.get(is_system_owner=True)
            owner_safe = SafePartner.objects.get(partner=owner, safe_type__name="قاسە")
            adjust_safe_balance(
                owner_safe, instance.my_bonus, instance.bonus_currency, add=False
            )

            adjust_safe_balance(
                instance.to_partner,
                instance.partner_bonus,
                instance.bonus_currency,
                add=False,
            )

            if instance.from_partner:
                adjust_safe_balance(
                    instance.from_partner,
                    instance.money_amount,
                    instance.currency,
                    add=True,
                )


# *************************
# Safe Transactions
# *************************


@receiver(post_save, sender=SafeTransaction)
def safe_transaction_post_save(sender, instance, created, **kwargs):
    """
    Handle balance updates when SafeTransaction is created
    """
    if not created:
        # Only process new transactions to avoid duplicate processing
        return

    handle_safe_transaction(instance)


def handle_safe_transaction(instance):
    """
    Add or subtract money_amount to/from partner based on transaction_type and currency
    """
    with transaction.atomic():
        partner = instance.partner
        amount = Decimal(instance.money_amount)

        if instance.transaction_type == "ADD":
            # Add money to partner's balance
            if instance.currency == "USDT":
                partner.total_usdt += amount
            elif instance.currency == "USD":
                partner.total_usd += amount
            elif instance.currency == "IQD":
                partner.total_iqd += amount

        elif instance.transaction_type == "REMOVE":
            # Subtract money from partner's balance
            if instance.currency == "USDT":
                partner.total_usdt -= amount
            elif instance.currency == "USD":
                partner.total_usd -= amount
            elif instance.currency == "IQD":
                partner.total_iqd -= amount

        # Save the updated partner balance
        partner.save()
