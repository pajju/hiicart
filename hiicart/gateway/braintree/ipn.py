import braintree
from datetime import datetime
from decimal import Decimal
from hiicart.gateway.base import IPNBase
from hiicart.gateway.braintree.settings import SETTINGS as default_settings
from hiicart.models import CART_TYPES


class BraintreeIPN(IPNBase):
    """Braintree IPN Handler."""

    def __init__(self, cart):
        super(BraintreeIPN, self).__init__("braintree", cart, default_settings)
        self._require_settings(["MERCHANT_ID", "MERCHANT_KEY", "MERCHANT_PRIVATE_KEY"])
        braintree.Configuration.configure(self.environment, 
                                          self.settings["MERCHANT_ID"], 
                                          self.settings["MERCHANT_KEY"],
                                          self.settings["MERCHANT_PRIVATE_KEY"])

    @property
    def environment(self):
        if self.settings["LIVE"]:
            return braintree.Environment.Production
        else:
            return braintree.Environment.Sandbox

    def _record_payment(self, transaction):
        """Create a new payment record."""
        if not self.cart:
            return
        if transaction.status == "settled" or transaction.status == "authorized":
            state = "PAID"
        elif transaction.status == "authorizing" or transaction.status == "submitted_for_settlement":
            state = "PENDING"
        else:
            return
        pending = self.cart.payments.filter(state="PENDING", transaction_id=transaction.id)
        if pending:
            pending[0].state = state
            pending[0].save()
            return pending[0]
        else:
            payment = self._create_payment(transaction.amount, transaction.id, state)
            payment.save()
            return payment

    def new_order(self, transaction):
        """Save a new order."""
        if not self.cart:
            return
        self.cart.ship_first_name = transaction.shipping["first_name"] or self.cart.ship_first_name
        self.cart.ship_last_name = transaction.shipping["last_name"] or self.cart.ship_last_name
        self.cart.ship_street1 = transaction.shipping["street_address"] or self.cart.ship_street1
        self.cart.ship_street2 = transaction.shipping["extended_address"] or self.cart.ship_street2
        self.cart.ship_city = transaction.shipping["locality"] or self.cart.ship_city
        self.cart.ship_state = transaction.shipping["region"] or self.cart.ship_state
        self.cart.ship_postal_code = transaction.shipping["postal_code"] or self.cart.ship_postal_code
        self.cart.ship_country = transaction.shipping["country_code_alpha2"] or self.cart.ship_country
        self.cart.bill_first_name = transaction.billing["first_name"] or self.cart.bill_first_name
        self.cart.bill_last_name = transaction.billing["last_name"] or self.cart.bill_last_name
        self.cart.bill_street1 = transaction.billing["street_address"] or self.cart.bill_street1
        self.cart.bill_street2 = transaction.billing["extended_address"] or self.cart.bill_street2
        self.cart.bill_city = transaction.billing["locality"] or self.cart.bill_city
        self.cart.bill_state = transaction.billing["region"] or self.cart.bill_state
        self.cart.bill_postal_code = transaction.billing["postal_code"] or self.cart.bill_postal_code
        self.cart.bill_country = transaction.billing["country_code_alpha2"] or self.cart.bill_country
        self.cart._cart_state = "SUBMITTED"
        self.cart.save()
        self._record_payment(transaction)

    def update_order_status(self, transaction_id):
        """
        Check the state of a Braintree transaction and update the order.

        Return True if the payment has Settled, or False otherwise.
        """
        transaction = braintree.Transaction.find(transaction_id)
        # Force settlement on dev
        if not self.settings["LIVE"]:
            transaction.status = u"settled"
        if transaction:
            payment = self._record_payment(transaction)
            if payment.state == "PAID":
                self.cart.set_state("COMPLETED")
                self.cart._cart_state
                return True
        return False