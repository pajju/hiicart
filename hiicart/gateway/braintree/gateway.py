import braintree

from django.template import Context, loader

from hiicart.gateway.base import PaymentGatewayBase, CancelResult, SubmitResult, PaymentResult
from hiicart.gateway.braintree.forms import PaymentForm
from hiicart.gateway.braintree.ipn import BraintreeIPN
from hiicart.gateway.braintree.settings import SETTINGS as default_settings
from hiicart.gateway.braintree.tasks import update_payment_status


class BraintreeGateway(PaymentGatewayBase):
    """Payment Gateway for Braintree."""

    def __init__(self, cart):
        super(BraintreeGateway, self).__init__("braintree", cart, default_settings)
        self._require_settings(["MERCHANT_ID", "MERCHANT_KEY",
                                "MERCHANT_PRIVATE_KEY"])
        braintree.Configuration.configure(self.environment,
                                          self.settings["MERCHANT_ID"],
                                          self.settings["MERCHANT_KEY"],
                                          self.settings["MERCHANT_PRIVATE_KEY"])

    def _is_valid(self):
        """Return True if gateway is valid."""
        # TODO: Query Braintree to validate credentials
        return True

    @property
    def is_recurring(self):
        return self.cart.recurring_lineitems > 0

    @property
    def environment(self):
        """Determine which Braintree environment to use."""
        if self.settings["LIVE"]:
            return braintree.Environment.Production
        else:
            return braintree.Environment.Sandbox

    def submit(self, collect_address=False, cart_settings_kwargs=None, submit=False):
        """
        Simply returns the gateway type to let the frontend know how to proceed.
        """
        return SubmitResult("direct")

    @property
    def form(self):
        """Returns an instance of PaymentForm."""
        return PaymentForm()

    def start_transaction(self, request):
        """Submits transaction details to Braintree and returns form data."""
        tr_data = braintree.Transaction.tr_data_for_sale({
            "transaction": {"type": "sale",
                            "order_id": self.cart.cart_uuid,
                            "amount": self.cart.total,
                            "options": {
                                "submit_for_settlement": True,
                                "store_in_vault": self.is_recurring
                            }}},
            request.build_absolute_uri(request.path))
        return tr_data

    def confirm_payment(self, request):
        """
        Confirms payment result with Braintree.

        This method should be called after the Braintree transaction redirect
        to determine the payment result. It expects the request to contain the
        query string coming back from Braintree.
        """
        try:
            result = braintree.TransparentRedirect.confirm(request.META['QUERY_STRING'])
        except Exception, e:
            errors = {'non_field_errors': 'Request to payment gateway failed.'}
            return PaymentResult(transaction_id=None, success=False,
                                 status=None, errors=errors)

        if result.is_success:
            handler = BraintreeIPN(self.cart)
            created = handler.new_order(result.transaction)
            if created:
                # If this is a subscription purchase, set up a subscription with Braintree
                if self.is_recurring:
                    item = self.cart.recurring_lineitems[0]
                    gateway_plan_id = item.gateway_plan_id
                    payment_token = result.transaction.credit_card['token']
                    subscribe_result = braintree.Subscription.create({
                        'payment_method_token': payment_token,
                        'plan_id': gateway_plan_id})
                    # TODO: Save subscription id to recurringlineitem
                return PaymentResult(transaction_id=result.transaction.id,
                                     success=True,
                                     status=result.transaction.status)
        errors = {}
        if not result.transaction:
            transaction_id = None
            status = None
            for error in result.errors.deep_errors:
                errors[error.attribute] = error.message
        else:
            transaction_id = result.transaction.id
            status = result.transaction.status
            if result.transaction.status == "processor_declined":
                errors = {'non_field_errors': result.transaction.processor_response_text}
            elif result.transaction.status == "gateway_rejected":
                errors = {'non_field_errors': result.transaction.gateway_rejection_reason}
        return PaymentResult(transaction_id=transaction_id, success=False,
                             status=status, errors=errors)

    def update_payment_status(self, transaction_id):
        update_payment_status.apply_async(args=[self.cart.id, transaction_id], countdown=300)

    
    def apply_discount(self, subscription_id, discount_id, num_billing_cycles=1, quantity=1):
        subscription = braintree.Subscription.find(subscription_id)
        existing_discounts = filter(subscription.discounts, lambda d: d.id==discount_id)
        if not existing_discounts:
            result = braintree.Subscription.update(subscription_id, {
                'discounts': {
                    'add': [
                        {
                            'inherited_from_id': discount_id,
                            'number_of_billing_cycles': num_billing_cycles,
                            'quantity': quantity
                        }
                    ]
                }
            })
        else:
            existing_cycles = existing_discounts[0].number_of_billing_cycles
            result = braintree.Subscription.update(subscription_id, {
                'discounts': {
                    'update': [
                        {
                            'existing_id': discount_id,
                            'number_of_billing_cycles': existing_cycles + num_billing_cycles,
                            'quantity': quantity
                        }
                    ]
                }
            })
        if not result.is_success:
            raise GatewayException(result.message or 'There was an error applying the discount')
        return result.subscription

        
