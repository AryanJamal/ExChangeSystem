from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
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
    Debt,
    DebtRepayment,
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
            partner.total_usd -= Decimal(instance.usd_amount)
            partner.total_iqd += instance.iqd_amount

        elif instance.exchange_type == "IQD_TO_USD":
            partner.total_iqd -= instance.iqd_amount
            partner.total_usd += Decimal(instance.usd_amount)
        if instance.bonus_currency == "USD":
            partner.total_usd += Decimal(instance.my_bonus)
        if instance.bonus_currency == "IQD":
            partner.total_iqd += instance.my_bonus

        partner.save()


@receiver(post_delete, sender=TransferExchange)
def transfer_exchange_post_delete(sender, instance, **kwargs):
    with transaction.atomic():
        partner = instance.partner

        if instance.exchange_type == "USD_TO_IQD":
            partner.total_usd += Decimal(instance.usd_amount)
            partner.total_iqd -= instance.iqd_amount

        elif instance.exchange_type == "IQD_TO_USD":
            partner.total_iqd += instance.iqd_amount
            partner.total_usd -= Decimal(instance.usd_amount)
        if instance.bonus_currency == "USD":
            partner.total_usd -= Decimal(instance.my_bonus)
        if instance.bonus_currency == "IQD":
            partner.total_iqd -= instance.my_bonus

        partner.save()


# *************************
# Crypto
# *************************
@receiver(pre_save, sender=CryptoTransaction)
def crypto_txn_pre_save(sender, instance, **kwargs):
    """
    Store old values to compare during update
    """
    if instance.pk:
        try:
            old = CryptoTransaction.objects.get(pk=instance.pk)
            instance._old_status = old.status
            instance._old_bonus = old.bonus
        except CryptoTransaction.DoesNotExist:
            instance._old_status = None
            instance._old_bonus = Decimal("0")
    else:
        instance._old_status = None
        instance._old_bonus = Decimal("0")


@receiver(post_save, sender=CryptoTransaction)
def crypto_txn_post_save(sender, instance, created, **kwargs):
    try:
        owner = Partner.objects.get(is_system_owner=True)
        payment_safe = SafePartner.objects.get(
            partner=owner, safe_type=instance.payment_safe
        )
        crypto_safe = SafePartner.objects.get(
            partner=owner, safe_type=instance.crypto_safe
        )
    except (Partner.DoesNotExist, SafePartner.DoesNotExist):
        return

    with transaction.atomic():
        if created:
            if instance.transaction_type == "Buy":
                crypto_safe.total_usdt += Decimal(instance.usdt_amount)
            elif instance.transaction_type == "Sell":
                crypto_safe.total_usdt -= Decimal(instance.usdt_amount)

            if instance.status == "Completed":
                _apply_fiat_and_bonus(instance, payment_safe, crypto_safe)

        # ---------------- On Update ----------------
        else:
            # Status changed Pending -> Completed
            if instance._old_status == "Pending" and instance.status == "Completed":
                _apply_fiat_and_bonus(instance, payment_safe, crypto_safe)

        crypto_safe.save()
        payment_safe.save()
        if instance.partner:
            instance.partner.save()


@receiver(post_delete, sender=CryptoTransaction)
def crypto_txn_post_delete(sender, instance, **kwargs):
    """
    Reverse balances when a transaction is deleted
    """
    try:
        owner = Partner.objects.get(is_system_owner=True)
        payment_safe = SafePartner.objects.get(
            partner=owner, safe_type=instance.payment_safe
        )
        crypto_safe = SafePartner.objects.get(
            partner=owner, safe_type=instance.crypto_safe
        )
    except (Partner.DoesNotExist, SafePartner.DoesNotExist):
        return

    with transaction.atomic():
        # Reverse USDT balance
        if instance.transaction_type == "Buy":
            crypto_safe.total_usdt -= Decimal(instance.usdt_amount)
        elif instance.transaction_type == "Sell":
            crypto_safe.total_usdt += Decimal(instance.usdt_amount)

        # Reverse fiat + bonus only if Completed
        if instance.status == "Completed":
            _reverse_fiat_and_bonus(instance, payment_safe, crypto_safe)

        crypto_safe.save()
        payment_safe.save()
        if instance.partner:
            instance.partner.save()


# ----------------- Helper functions -----------------


def _apply_fiat_and_bonus(instance, payment_safe, crypto_safe):
    """Apply fiat movement and bonus distribution"""
    # Fiat side
    if instance.currency == "USD":
        if instance.transaction_type == "Buy":
            payment_safe.total_usd -= Decimal(instance.usdt_price)
        else:  # Sell
            payment_safe.total_usd += Decimal(instance.usdt_price)
    elif instance.currency == "IQD":
        if instance.transaction_type == "Buy":
            payment_safe.total_iqd -= Decimal(instance.usdt_price)
        else:
            payment_safe.total_iqd += Decimal(instance.usdt_price)

    # Bonus
    _apply_bonus_diff(instance, payment_safe, crypto_safe, instance.bonus)


def _apply_bonus_diff(instance, payment_safe, crypto_safe, bonus_diff):
    """Distribute bonus difference (can be positive or negative)"""
    if bonus_diff == 0:
        return

    if instance.partner:
        partner_share = bonus_diff / Decimal("2")
        owner_share = bonus_diff - partner_share
    else:
        partner_share = Decimal("0")
        owner_share = bonus_diff

    if instance.bonus_currency == "USDT":
        crypto_safe.total_usdt += owner_share
        if instance.partner:
            instance.partner.total_usdt += partner_share
    elif instance.bonus_currency == "USD":
        payment_safe.total_usd += owner_share
        if instance.partner:
            instance.partner.total_usd += partner_share
    elif instance.bonus_currency == "IQD":
        payment_safe.total_iqd += owner_share
        if instance.partner:
            instance.partner.total_iqd += partner_share


def _reverse_fiat_and_bonus(instance, payment_safe, crypto_safe):
    """Reverse fiat + bonus when deleting"""
    # Fiat side (reverse sign)
    if instance.currency == "USD":
        if instance.transaction_type == "Buy":
            payment_safe.total_usd += Decimal(instance.usdt_price)
        else:
            payment_safe.total_usd -= Decimal(instance.usdt_price)
    elif instance.currency == "IQD":
        if instance.transaction_type == "Buy":
            payment_safe.total_iqd += Decimal(instance.usdt_price)
        else:
            payment_safe.total_iqd -= Decimal(instance.usdt_price)

    # Bonus (reverse sign)
    _apply_bonus_diff(instance, payment_safe, crypto_safe, -instance.bonus)


# *************************
# Incoming Money
# *************************


def adjust_balance(safe_partner, amount, currency):
    if not safe_partner:
        return
    if currency == "USD":
        safe_partner.total_usd = safe_partner.total_usd + amount
    elif currency == "IQD":
        safe_partner.total_iqd = safe_partner.total_iqd + amount
    safe_partner.save(update_fields=["total_usd", "total_iqd"])


def get_owner_safe():
    owner_partner = Partner.objects.get(is_system_owner=True)
    return SafePartner.objects.get(partner=owner_partner, safe_type__name="قاسە")


@receiver(pre_save, sender=IncomingMoney)
def before_update_incoming(sender, instance, **kwargs):
    """Keep track of old values for update handling"""
    if instance.pk:
        try:
            old = IncomingMoney.objects.get(pk=instance.pk)
            instance._old_status = old.status
            instance._old_money_amount = old.money_amount
            instance._old_currency = old.currency
            instance._old_my_bonus = old.my_bonus
            instance._old_partner_bonus = old.partner_bonus
            instance._old_bonus_currency = old.bonus_currency
        except IncomingMoney.DoesNotExist:
            pass


@receiver(post_save, sender=IncomingMoney)
def after_save_incoming(sender, instance, created, **kwargs):
    from_partner = instance.from_partner
    to_partner = instance.to_partner
    owner_safe = get_owner_safe()

    # ✅ On Create
    if created:
        # Subtract from from_partner immediately
        adjust_balance(from_partner, -instance.money_amount, instance.currency)

        if instance.status == "Completed":
            # Credit to_partner
            if to_partner:
                adjust_balance(to_partner, instance.money_amount, instance.currency)
            # Add bonuses
            adjust_balance(owner_safe, instance.my_bonus, instance.bonus_currency)
            adjust_balance(
                from_partner, instance.partner_bonus, instance.bonus_currency
            )

    else:
        # ✅ On Update
        old_status = getattr(instance, "_old_status", None)

        # If status changed from Pending → Completed
        if old_status == "Pending" and instance.status == "Completed":
            if to_partner:
                adjust_balance(to_partner, instance.money_amount, instance.currency)
            adjust_balance(owner_safe, instance.my_bonus, instance.bonus_currency)
            adjust_balance(
                from_partner, instance.partner_bonus, instance.bonus_currency
            )

        # If already completed, check for amount/bonus changes
        elif instance.status == "Completed":
            old_amount = getattr(instance, "_old_money_amount", instance.money_amount)
            old_currency = getattr(instance, "_old_currency", instance.currency)
            old_my_bonus = getattr(instance, "_old_my_bonus", instance.my_bonus)
            old_partner_bonus = getattr(
                instance, "_old_partner_bonus", instance.partner_bonus
            )
            old_bonus_currency = getattr(
                instance, "_old_bonus_currency", instance.bonus_currency
            )

            # rollback old values
            if to_partner:
                adjust_balance(to_partner, -old_amount, old_currency)
            adjust_balance(owner_safe, -old_my_bonus, old_bonus_currency)
            adjust_balance(from_partner, -old_partner_bonus, old_bonus_currency)

            # apply new values
            if to_partner:
                adjust_balance(to_partner, instance.money_amount, instance.currency)
            adjust_balance(owner_safe, instance.my_bonus, instance.bonus_currency)
            adjust_balance(
                from_partner, instance.partner_bonus, instance.bonus_currency
            )


@receiver(post_delete, sender=IncomingMoney)
def after_delete_incoming(sender, instance, **kwargs):
    from_partner = instance.from_partner
    to_partner = instance.to_partner
    owner_safe = get_owner_safe()

    # Revert subtraction from from_partner
    adjust_balance(from_partner, instance.money_amount, instance.currency)

    if instance.status == "Completed":
        if to_partner:
            adjust_balance(to_partner, -instance.money_amount, instance.currency)
        adjust_balance(owner_safe, -instance.my_bonus, instance.bonus_currency)
        adjust_balance(from_partner, -instance.partner_bonus, instance.bonus_currency)


# *************************
# Outgoing Money
# *************************
@receiver(pre_save, sender=OutgoingMoney)
def outgoing_money_pre_save(sender, instance, **kwargs):
    """
    Store old status and bonuses before saving to detect updates
    """
    instance._old_status = None
    instance._old_my_bonus = Decimal("0")
    instance._old_partner_bonus = Decimal("0")

    if instance.pk:
        try:
            old_instance = OutgoingMoney.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
            instance._old_my_bonus = old_instance.my_bonus
            instance._old_partner_bonus = old_instance.partner_bonus
        except OutgoingMoney.DoesNotExist:
            pass


# --- POST_SAVE: handle create or update ---
@receiver(post_save, sender=OutgoingMoney)
def outgoing_money_post_save(sender, instance, created, **kwargs):
    """
    Handle money movements and bonuses on creation and status updates
    """
    try:
        owner_partner = Partner.objects.get(is_system_owner=True)
        owner_safe = SafePartner.objects.get(
            partner=owner_partner, safe_type__name="قاسە"
        )
    except (Partner.DoesNotExist, SafePartner.DoesNotExist):
        return  # Cannot proceed without owner and their safe

    with transaction.atomic():
        # --- Handle creation ---
        if created:
            # Add money_amount to to_partner
            if instance.to_partner:
                if instance.currency == "USD":
                    instance.to_partner.total_usd += Decimal(instance.money_amount)
                elif instance.currency == "IQD":
                    instance.to_partner.total_iqd += Decimal(instance.money_amount)
                instance.to_partner.save()

            # If status is Completed, apply bonuses and from_partner deduction
            if instance.status == "Completed":
                # Deduct from from_partner if exists
                if instance.from_partner:
                    if instance.currency == "USD":
                        instance.from_partner.total_usd -= Decimal(
                            instance.money_amount
                        )
                    elif instance.currency == "IQD":
                        instance.from_partner.total_iqd -= Decimal(
                            instance.money_amount
                        )
                    instance.from_partner.save()

                # Add my_bonus to owner
                if instance.bonus_currency == "USD":
                    owner_safe.total_usd += Decimal(instance.my_bonus)
                elif instance.bonus_currency == "IQD":
                    owner_safe.total_iqd += Decimal(instance.my_bonus)
                owner_safe.save()

                # Add partner_bonus to to_partner if exists
                if instance.to_partner:
                    if instance.bonus_currency == "USD":
                        instance.to_partner.total_usd += Decimal(instance.partner_bonus)
                    elif instance.bonus_currency == "IQD":
                        instance.to_partner.total_iqd += Decimal(instance.partner_bonus)
                    instance.to_partner.save()

        # --- Handle update ---
        else:
            # Only apply logic if status changed to Completed
            old_status = getattr(instance, "_old_status", None)
            if old_status != "Completed" and instance.status == "Completed":
                # Deduct from from_partner if exists
                if instance.from_partner:
                    if instance.currency == "USD":
                        instance.from_partner.total_usd -= Decimal(
                            instance.money_amount
                        )
                    elif instance.currency == "IQD":
                        instance.from_partner.total_iqd -= Decimal(
                            instance.money_amount
                        )
                    instance.from_partner.save()

                # Add my_bonus to owner (use new bonus amount)
                if instance.bonus_currency == "USD":
                    owner_safe.total_usd += Decimal(instance.my_bonus)
                elif instance.bonus_currency == "IQD":
                    owner_safe.total_iqd += Decimal(instance.my_bonus)
                owner_safe.save()

                # Add partner_bonus to to_partner if exists
                if instance.to_partner:
                    if instance.bonus_currency == "USD":
                        instance.to_partner.total_usd += Decimal(instance.partner_bonus)
                    elif instance.bonus_currency == "IQD":
                        instance.to_partner.total_iqd += Decimal(instance.partner_bonus)
                    instance.to_partner.save()


# --- POST_DELETE: rollback money movements and bonuses ---
@receiver(post_delete, sender=OutgoingMoney)
def outgoing_money_post_delete(sender, instance, **kwargs):
    """
    Rollback money movements and bonuses when an OutgoingMoney is deleted
    """
    try:
        owner_partner = Partner.objects.get(is_system_owner=True)
        owner_safe = SafePartner.objects.get(
            partner=owner_partner, safe_type__name="قاسە"
        )
    except (Partner.DoesNotExist, SafePartner.DoesNotExist):
        return

    with transaction.atomic():
        # Remove money_amount from to_partner
        if instance.to_partner:
            if instance.currency == "USD":
                instance.to_partner.total_usd -= Decimal(instance.money_amount)
            elif instance.currency == "IQD":
                instance.to_partner.total_iqd -= Decimal(instance.money_amount)
            instance.to_partner.save()

        # If status was Completed, rollback bonuses and from_partner deduction
        if instance.status == "Completed":
            # Refund from_partner if exists
            if instance.from_partner:
                if instance.currency == "USD":
                    instance.from_partner.total_usd += Decimal(instance.money_amount)
                elif instance.currency == "IQD":
                    instance.from_partner.total_iqd += Decimal(instance.money_amount)
                instance.from_partner.save()

            # Remove my_bonus from owner
            if instance.bonus_currency == "USD":
                owner_safe.total_usd -= Decimal(instance.my_bonus)
            elif instance.bonus_currency == "IQD":
                owner_safe.total_iqd -= Decimal(instance.my_bonus)
            owner_safe.save()

            # Remove partner_bonus from to_partner if exists
            if instance.to_partner:
                if instance.bonus_currency == "USD":
                    instance.to_partner.total_usd -= Decimal(instance.partner_bonus)
                elif instance.bonus_currency == "IQD":
                    instance.to_partner.total_iqd -= Decimal(instance.partner_bonus)
                instance.to_partner.save()


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


@receiver(post_delete, sender=SafeTransaction)
def safe_transaction_post_delete(sender, instance, **kwargs):
    """
    Reverse the balance update when a SafeTransaction is deleted.
    """
    handle_safe_transaction_reverse(instance)


def handle_safe_transaction_reverse(instance):
    """
    Reverse the add or subtract money_amount to/from partner based on transaction_type and currency.
    """
    with transaction.atomic():
        partner = instance.partner
        amount = Decimal(instance.money_amount)

        if instance.transaction_type == "ADD":
            # If the original transaction added money, we subtract it back.
            if instance.currency == "USDT":
                partner.total_usdt -= amount
            elif instance.currency == "USD":
                partner.total_usd -= amount
            elif instance.currency == "IQD":
                partner.total_iqd -= amount

        elif instance.transaction_type == "REMOVE":
            # If the original transaction removed money, we add it back.
            if instance.currency == "USDT":
                partner.total_usdt += amount
            elif instance.currency == "USD":
                partner.total_usd += amount
            elif instance.currency == "IQD":
                partner.total_iqd += amount

        partner.save()


# *************************
# Debt
# *************************
def get_system_owner_safe_partner(debt):
    """Return SafePartner for system owner + the chosen safe."""
    try:
        system_owner = Partner.objects.get(is_system_owner=True)
        safe_partner = SafePartner.objects.get(
            partner=system_owner, safe_type=debt.debt_safe
        )
        return safe_partner
    except (Partner.DoesNotExist, SafePartner.DoesNotExist):
        return None


# -----------------------------
# Debt Signals
# -----------------------------
@receiver(post_save, sender=Debt)
def handle_debt_created(sender, instance, created, **kwargs):
    if created:
        safe_partner = get_system_owner_safe_partner(instance)
        if not safe_partner:
            return

        if instance.currency == "USD":
            safe_partner.total_usd -= instance.total_amount
        elif instance.currency == "IQD":
            safe_partner.total_iqd -= int(instance.total_amount)
        safe_partner.save()


@receiver(post_delete, sender=Debt)
def handle_debt_deleted(sender, instance, **kwargs):
    safe_partner = get_system_owner_safe_partner(instance)
    if not safe_partner:
        return

    # When deleting debt, restore the money back
    if instance.currency == "USD":
        safe_partner.total_usd += instance.total_amount
    elif instance.currency == "IQD":
        safe_partner.total_iqd += int(instance.total_amount)
    safe_partner.save()


# -----------------------------
# Repayment Signals
# -----------------------------
@receiver(post_save, sender=DebtRepayment)
def handle_repayment_created(sender, instance, created, **kwargs):
    if created:
        debt = instance.debt
        safe_partner = get_system_owner_safe_partner(debt)
        if not safe_partner:
            return

        if debt.currency == "USD":
            safe_partner.total_usd += instance.amount
        elif debt.currency == "IQD":
            safe_partner.total_iqd += int(instance.amount)
        safe_partner.save()


@receiver(post_delete, sender=DebtRepayment)
def handle_repayment_deleted(sender, instance, **kwargs):
    debt = instance.debt
    safe_partner = get_system_owner_safe_partner(debt)
    if not safe_partner:
        return

    # Remove repayment → subtract from balances
    if debt.currency == "USD":
        safe_partner.total_usd -= instance.amount
    elif debt.currency == "IQD":
        safe_partner.total_iqd -= int(instance.amount)
    safe_partner.save()
