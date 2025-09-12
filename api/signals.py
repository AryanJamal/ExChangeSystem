from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.db import transaction, models
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
            if not instance.is_received:
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
            if not instance.is_received:
                if to_partner:
                    if to_partner == owner_safe:
                        adjust_balance(
                            owner_safe, instance.money_amount, instance.currency
                        )
                    else:
                        adjust_balance(
                            to_partner, instance.money_amount, instance.currency
                        )
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
            if not instance.is_received:
                if to_partner:
                    adjust_balance(to_partner, -old_amount, old_currency)
            adjust_balance(owner_safe, -old_my_bonus, old_bonus_currency)
            adjust_balance(from_partner, -old_partner_bonus, old_bonus_currency)

            # apply new values
            if not instance.is_received:
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
        if not instance.is_received:
            if to_partner:
                if to_partner == owner_safe:
                    adjust_balance(
                        owner_safe, -instance.money_amount, instance.currency
                    )
                else:
                    adjust_balance(
                        to_partner, -instance.money_amount, instance.currency
                    )
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
            if not instance.is_received:
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
                    if instance.from_partner == owner_safe:  # if it's the system owner
                        if instance.currency == "USD":
                            owner_safe.total_usd -= Decimal(instance.money_amount)
                        elif instance.currency == "IQD":
                            owner_safe.total_iqd -= Decimal(instance.money_amount)
                        owner_safe.save()
                    else:
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
                if not instance.is_received:
                    if instance.to_partner:
                        if instance.bonus_currency == "USD":
                            instance.to_partner.total_usd += Decimal(
                                instance.partner_bonus
                            )
                        elif instance.bonus_currency == "IQD":
                            instance.to_partner.total_iqd += Decimal(
                                instance.partner_bonus
                            )
                        instance.to_partner.save()

        # --- Handle update ---
        else:
            # Only apply logic if status changed to Completed
            old_status = getattr(instance, "_old_status", None)
            if old_status != "Completed" and instance.status == "Completed":
                # Deduct from from_partner if exists
                if instance.from_partner:
                    if instance.from_partner == owner_safe:  # if it's the system owner
                        if instance.currency == "USD":
                            owner_safe.total_usd -= Decimal(instance.money_amount)
                        elif instance.currency == "IQD":
                            owner_safe.total_iqd -= Decimal(instance.money_amount)
                        owner_safe.save()
                    else:
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
                if not instance.is_received:
                    if instance.to_partner:
                        if instance.bonus_currency == "USD":
                            instance.to_partner.total_usd += Decimal(
                                instance.partner_bonus
                            )
                        elif instance.bonus_currency == "IQD":
                            instance.to_partner.total_iqd += Decimal(
                                instance.partner_bonus
                            )
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
        if not instance.is_received:
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
                if instance.from_partner == owner_safe:  # if it's the system owner
                    if instance.currency == "USD":
                        owner_safe.total_usd += Decimal(instance.money_amount)
                    elif instance.currency == "IQD":
                        owner_safe.total_iqd += Decimal(instance.money_amount)
                    owner_safe.save()
                else:
                    if instance.currency == "USD":
                        instance.from_partner.total_usd += Decimal(
                            instance.money_amount
                        )
                    elif instance.currency == "IQD":
                        instance.from_partner.total_iqd += Decimal(
                            instance.money_amount
                        )
                    instance.from_partner.save()

            # Remove my_bonus from owner
            if instance.bonus_currency == "USD":
                owner_safe.total_usd -= Decimal(instance.my_bonus)
            elif instance.bonus_currency == "IQD":
                owner_safe.total_iqd -= Decimal(instance.my_bonus)
            owner_safe.save()

            # Remove partner_bonus from to_partner if exists
            if not instance.is_received:
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
    Handle balance updates when a SafePartnerTransaction is created.
    """
    if not created:
        # Only process new transactions
        return

    handle_safe_transaction(instance)


def handle_safe_transaction(instance):
    """
    Updates safe partner balances based on the transaction type.
    """
    with transaction.atomic():
        amount = Decimal(instance.money_amount)
        currency = instance.currency

        if instance.transaction_type == "ADD":
            # Adds money to the specified partner.
            partner = instance.partner
            if currency == "USDT":
                partner.total_usdt += amount
            elif currency == "USD":
                partner.total_usd += amount
            elif currency == "IQD":
                partner.total_iqd += amount
            partner.save()

        elif instance.transaction_type == "REMOVE":
            # Subtracts money from the specified partner.
            partner = instance.partner
            if currency == "USDT":
                partner.total_usdt -= amount
            elif currency == "USD":
                partner.total_usd -= amount
            elif currency == "IQD":
                partner.total_iqd -= amount
            partner.save()

        elif instance.transaction_type == "EXPENSE":
            # Subtracts money from the specified partner.
            partner = instance.partner
            if currency == "USDT":
                partner.total_usdt -= amount
            elif currency == "USD":
                partner.total_usd -= amount
            elif currency == "IQD":
                partner.total_iqd -= amount
            partner.save()

        elif instance.transaction_type == "TRANSFER":
            # Transfers money from one partner to another.
            from_partner = instance.from_safepartner
            to_partner = instance.to_safepartner

            # Debit the 'from' partner
            if currency == "USDT":
                from_partner.total_usdt -= amount
            elif currency == "USD":
                from_partner.total_usd -= amount
            elif currency == "IQD":
                from_partner.total_iqd -= amount

            # Credit the 'to' partner
            if currency == "USDT":
                to_partner.total_usdt += amount
            elif currency == "USD":
                to_partner.total_usd += amount
            elif currency == "IQD":
                to_partner.total_iqd += amount

            # Save both partners within the atomic block
            from_partner.save()
            to_partner.save()


@receiver(post_delete, sender=SafeTransaction)
def safe_transaction_post_delete(sender, instance, **kwargs):
    """
    Reverses the balance update when a SafePartnerTransaction is deleted.
    """
    handle_safe_transaction_reverse(instance)


def handle_safe_transaction_reverse(instance):
    """
    Reverses the balance update for any transaction type.
    """
    with transaction.atomic():
        amount = Decimal(instance.money_amount)
        currency = instance.currency

        if instance.transaction_type == "ADD":
            # Reverses an 'ADD' transaction by subtracting.
            partner = instance.partner
            if currency == "USDT":
                partner.total_usdt -= amount
            elif currency == "USD":
                partner.total_usd -= amount
            elif currency == "IQD":
                partner.total_iqd -= amount
            partner.save()

        elif instance.transaction_type == "REMOVE":
            # Reverses a 'REMOVE' transaction by adding.
            partner = instance.partner
            if currency == "USDT":
                partner.total_usdt += amount
            elif currency == "USD":
                partner.total_usd += amount
            elif currency == "IQD":
                partner.total_iqd += amount
            partner.save()
        
        elif instance.transaction_type == "EXPENSE":
            # Subtracts money from the specified partner.
            partner = instance.partner
            if currency == "USDT":
                partner.total_usdt += amount
            elif currency == "USD":
                partner.total_usd += amount
            elif currency == "IQD":
                partner.total_iqd += amount
            partner.save()

        elif instance.transaction_type == "TRANSFER":
            # Reverses a 'TRANSFER' by crediting the 'from' partner and debiting the 'to' partner.
            from_partner = instance.from_safepartner
            to_partner = instance.to_safepartner

            # Reverse the debit on the 'from' partner
            if currency == "USDT":
                from_partner.total_usdt += amount
            elif currency == "USD":
                from_partner.total_usd += amount
            elif currency == "IQD":
                from_partner.total_iqd += amount

            # Reverse the credit on the 'to' partner
            if currency == "USDT":
                to_partner.total_usdt -= amount
            elif currency == "USD":
                to_partner.total_usd -= amount
            elif currency == "IQD":
                to_partner.total_iqd -= amount

            # Save both partners
            from_partner.save()
            to_partner.save()


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
    if not created:
        return

    # Decide who pays: partner or system owner
    safe_partner = instance.safe_partner or get_system_owner_safe_partner(instance)
    if not safe_partner:
        return

    if instance.currency == "USD":
        safe_partner.total_usd -= instance.total_amount
    elif instance.currency == "USDT":
        safe_partner.total_usdt -= instance.total_amount
    elif instance.currency == "IQD":
        safe_partner.total_iqd -= instance.total_amount
    safe_partner.save()


# -----------------------------
# Repayment Signals
# -----------------------------
@receiver(post_save, sender=DebtRepayment)
def handle_repayment_created(sender, instance, created, **kwargs):
    if not created:
        return

    debt = instance.debt
    debtor_safe_partner = debt.safe_partner
    if not debtor_safe_partner:
        return

    # repayment converted into debt currency
    converted = instance.converted_amount(debt.currency)

    # already repaid before this repayment
    already_repaid = debt.amount_repaid - converted
    remaining_before = max(0, debt.total_amount - already_repaid)

    # split into normal vs extra (in debt currency)
    normal_repayment = min(converted, remaining_before)
    extra_amount = max(0, converted - remaining_before)

    # --------------------------------------
    # CASE 1: Same currency repayment
    # --------------------------------------
    if instance.currency == debt.currency:
        # always add (normal + extra) to debtor safe partner
        if instance.currency == "USD":
            debtor_safe_partner.total_usd += instance.amount
        elif instance.currency == "USDT":
            debtor_safe_partner.total_usdt += instance.amount
        elif instance.currency == "IQD":
            debtor_safe_partner.total_iqd += int(instance.amount)
        debtor_safe_partner.save()

    # --------------------------------------
    # CASE 2: Different currency repayment
    # --------------------------------------
    else:
        try:
            system_owner = Partner.objects.get(is_system_owner=True)
            owner_safe_partner_debt = SafePartner.objects.get(
                partner=system_owner, safe_type=debt.debt_safe
            )
            owner_safe_partner_repayment = SafePartner.objects.get(
                partner=system_owner, safe_type=instance.safe_type
            )
        except (Partner.DoesNotExist, SafePartner.DoesNotExist):
            return

        # 2a. Add converted normal repayment to debtor safe partner (in debt currency)
        if debt.currency == "USD":
            debtor_safe_partner.total_usd += normal_repayment
        elif debt.currency == "USDT":
            debtor_safe_partner.total_usdt += normal_repayment
        elif debt.currency == "IQD":
            debtor_safe_partner.total_iqd += int(normal_repayment)
        debtor_safe_partner.save()

        # 2b. Subtract converted normal repayment from owner's debt safe (in debt currency)
        if debt.currency == "USD":
            owner_safe_partner_debt.total_usd -= normal_repayment
        elif debt.currency == "USDT":
            owner_safe_partner_debt.total_usdt -= normal_repayment
        elif debt.currency == "IQD":
            owner_safe_partner_debt.total_iqd -= int(normal_repayment)
        owner_safe_partner_debt.save()

        # convert normal repayment (debt currency) back to repayment currency
        if instance.currency == "IQD":
            normal_in_repayment_currency = normal_repayment * instance.conversion_rate
        else:
            normal_in_repayment_currency = normal_repayment / instance.conversion_rate

        if instance.currency == "USD":
            owner_safe_partner_repayment.total_usd += normal_in_repayment_currency
        elif instance.currency == "USDT":
            owner_safe_partner_repayment.total_usdt += normal_in_repayment_currency
        elif instance.currency == "IQD":
            owner_safe_partner_repayment.total_iqd += int(normal_in_repayment_currency)
        owner_safe_partner_repayment.save()

        # 2d. Handle overpayment: subtract extra from owner’s repayment safe and add to debtor safe
        if extra_amount > 0:
            if instance.currency == "USD":
                debtor_safe_partner.total_usd += instance.amount - normal_repayment
            elif instance.currency == "USDT":
                debtor_safe_partner.total_usdt += instance.amount - normal_repayment
            elif instance.currency == "IQD":
                overpaid_iqd = int(
                    instance.amount - (normal_repayment / instance.conversion_rate)
                )
                debtor_safe_partner.total_iqd += overpaid_iqd

            debtor_safe_partner.save()


# -----------------------------
# Debt Delete Signals
# -----------------------------
@receiver(post_delete, sender=Debt)
def handle_debt_deleted(sender, instance, **kwargs):
    # Reverse the debt creation: add back the amount that was subtracted
    safe_partner = instance.safe_partner or get_system_owner_safe_partner(instance)
    if not safe_partner:
        return

    if instance.currency == "USD":
        safe_partner.total_usd += instance.total_amount
    elif instance.currency == "IQD":
        safe_partner.total_iqd += int(instance.total_amount)
    safe_partner.save()


@receiver(post_delete, sender=DebtRepayment)
def handle_repayment_deleted(sender, instance, **kwargs):
    """
    Handles the deletion of a DebtRepayment object by reversing the changes
    made when the repayment was created.
    """
    debt = instance.debt
    debtor_safe_partner = debt.safe_partner
    if not debtor_safe_partner:
        return

    # Repayment converted into debt currency
    converted = instance.converted_amount(debt.currency)

    # Already repaid after this repayment was made
    already_repaid = debt.amount_repaid + converted
    remaining_after = max(0, debt.total_amount - already_repaid)

    # Split into normal vs extra (in debt currency)
    normal_repayment = min(converted, remaining_after)
    extra_amount = max(0, converted - remaining_after)

    # --------------------------------------
    # CASE 1: Same currency repayment
    # --------------------------------------
    if instance.currency == debt.currency:
        # Subtract the full amount from the debtor's safe partner
        if instance.currency == "USD":
            debtor_safe_partner.total_usd -= instance.amount
        elif instance.currency == "USDT":
            debtor_safe_partner.total_usdt -= instance.amount
        elif instance.currency == "IQD":
            debtor_safe_partner.total_iqd -= int(instance.amount)
        debtor_safe_partner.save()

    # --------------------------------------
    # CASE 2: Different currency repayment
    # --------------------------------------
    else:
        try:
            system_owner = Partner.objects.get(is_system_owner=True)
            owner_safe_partner_debt = SafePartner.objects.get(
                partner=system_owner, safe_type=debt.debt_safe
            )
            owner_safe_partner_repayment = SafePartner.objects.get(
                partner=system_owner, safe_type=instance.safe_type
            )
        except (Partner.DoesNotExist, SafePartner.DoesNotExist):
            return

        # 2a. Subtract converted normal repayment from debtor safe partner (in debt currency)
        if debt.currency == "USD":
            debtor_safe_partner.total_usd -= normal_repayment
        elif debt.currency == "USDT":
            debtor_safe_partner.total_usdt -= normal_repayment
        elif debt.currency == "IQD":
            debtor_safe_partner.total_iqd -= int(normal_repayment)
        debtor_safe_partner.save()

        # 2b. Add converted normal repayment to owner's debt safe (in debt currency)
        if debt.currency == "USD":
            owner_safe_partner_debt.total_usd += normal_repayment
        elif debt.currency == "USDT":
            owner_safe_partner_debt.total_usdt += normal_repayment
        elif debt.currency == "IQD":
            owner_safe_partner_debt.total_iqd += int(normal_repayment)
        owner_safe_partner_debt.save()

        # convert normal repayment (debt currency) back to repayment currency
        if instance.currency == "IQD":
            normal_in_repayment_currency = normal_repayment * instance.conversion_rate
        else:
            normal_in_repayment_currency = normal_repayment / instance.conversion_rate

        # 2c. Subtract the normal repayment from the owner's repayment safe
        if instance.currency == "USD":
            owner_safe_partner_repayment.total_usd -= normal_in_repayment_currency
        elif instance.currency == "USDT":
            owner_safe_partner_repayment.total_usdt -= normal_in_repayment_currency
        elif instance.currency == "IQD":
            owner_safe_partner_repayment.total_iqd -= int(normal_in_repayment_currency)
        owner_safe_partner_repayment.save()

        # 2d. Handle overpayment: subtract overpaid amount from debtor safe
        if extra_amount > 0:
            if instance.currency == "USD":
                debtor_safe_partner.total_usd -= instance.amount - normal_repayment
            elif instance.currency == "USDT":
                debtor_safe_partner.total_usdt -= instance.amount - normal_repayment
            elif instance.currency == "IQD":
                overpaid_iqd = int(
                    instance.amount - (normal_repayment / instance.conversion_rate)
                )
                debtor_safe_partner.total_iqd -= overpaid_iqd
            debtor_safe_partner.save()
