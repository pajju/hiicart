import os
import urllib
import urllib2
import httplib2
from cgi import parse_qs

from decimal import Decimal
from datetime import datetime, timedelta
from django.contrib.sites.models import Site
from django.core import urlresolvers
from django.utils.http import urlencode
from django.utils.datastructures import SortedDict
from django.utils.safestring import mark_safe

from hiicart.gateway.base import PaymentGatewayBase, CancelResult, SubmitResult, GatewayError
from hiicart.gateway.paypal.settings import SETTINGS as default_settings

PAYMENT_CMD = {
    "BUY_NOW" : "_xclick",
    "CART" : "_cart",
    "SUBSCRIPTION" : "_xclick-subscriptions",
    "UNSUBSCRIBE" : "_subscr-find"
    }
NO_SHIPPING = {
    "REQUIRE": "2",
    "NO" : "1",
    "YES" : "0"
    }
NO_NOTE = {
    "NO" : "1",
    "YES" : "0"
    }
RECURRING_PAYMENT = {
    "YES" : "1",
    "NO" : "0"
    }

POST_URL = "https://www.paypal.com/cgi-bin/webscr"
POST_TEST_URL = "https://www.sandbox.paypal.com/cgi-bin/webscr"
NVP_SIGNATURE_TEST_URL = "https://api-3t.sandbox.paypal.com/nvp"
NVP_SIGNATURE_URL = "https://api-3t.paypal.com/nvp"

class PaypalGateway(PaymentGatewayBase):
    """Paypal payment processor"""

    def __init__(self, cart):
        super(PaypalGateway, self).__init__("paypal", cart, default_settings)
        self._require_settings(["BUSINESS"])
        if self.settings["ENCRYPT"]:
            self._require_settings(["PRIVATE_KEY", "PUBLIC_KEY", "PUBLIC_CERT_ID"])
            self.localprikey = self.settings["PRIVATE_KEY"]
            self.localpubkey = self.settings["PUBLIC_KEY"]
            self.paypalpubkey = os.path.abspath(os.path.join(
                os.path.dirname(__file__),
                "keys/paypal.%s.pem" % ("live" if self.settings["LIVE"] else "sandbox")))
            self._require_files([self.paypalpubkey, self.localpubkey, self.localprikey])
            try:
                import M2Crypto
            except ImportError:
                raise GatewayError("paypal_gateway: You must install M2Crypto to use an encrypted PayPal form.")

    @property
    def submit_url(self):
        if self.settings["LIVE"]:
            url = POST_URL
        else:
            url = POST_TEST_URL
        return mark_safe(url)

    @property
    def _nvp_url(self):
        """URL to post NVP API call to"""
        if self.settings['LIVE']:
            url = NVP_SIGNATURE_URL
        else:
            url = NVP_SIGNATURE_TEST_URL
        return mark_safe(url)

    def _do_nvp(self, method, params_dict):
        if not self.settings['API_USERNAME']:
            raise GatewayError("You must have NVP API credentials to do API operations (%s) with Paypal" % method)
        http = httplib2.Http()
        params_dict['method'] = method
        params_dict['user'] = self.settings['API_USERNAME']
        params_dict['pwd'] = self.settings['API_PASSWORD']
        params_dict['signature'] = self.settings['API_SIGNATURE']
        params_dict['version'] = self.settings['API_VERSION']
        encoded_params = urllib.urlencode(params_dict)
        response, content = http.request(self._nvp_url, 'POST', encoded_params)
        response_dict = parse_qs(content)
        for k, v in response_dict.iteritems():
            if type(v) == list:
                response_dict[k] = v[0]
        if response_dict['ACK'] != 'Success':
            print response_dict
            raise GatewayError("Error calling Paypal %s" % method)
        return response_dict

    def _encrypt_data(self, data):
        """
        Encrypt the form data.

        Refer to http://sandbox.rulemaker.net/ngps/m2/howto.smime.html
        """
        # Don't import at top because these are only required if user wants encryption
        from M2Crypto import BIO, SMIME, X509
        certid = self.settings["PUBLIC_CERT_ID"]
        # Assemble form data and encode in utf-8
        raw = ["cert_id=%s" % certid]
        raw.extend([u"%s=%s" % (key, val) for key, val in data.items() if val])
        raw = "\n".join(raw)
        raw = raw.encode("utf-8")
        self.log.debug('Encrypted Paypal data: %s' % raw)
        # make an smime object
        s = SMIME.SMIME()
        # load our public and private keys
        s.load_key_bio(BIO.openfile(self.localprikey),
                       BIO.openfile(self.localpubkey))
        # put the data in the buffer
        buf = BIO.MemoryBuffer(raw)
        # sign the text
        p7 = s.sign(buf, flags=SMIME.PKCS7_BINARY)
        # Load target cert to encrypt to.
        x509 = X509.load_cert_bio(BIO.openfile(self.paypalpubkey))
        sk = X509.X509_Stack()
        sk.push(x509)
        s.set_x509_stack(sk)
        # Set cipher: 3-key triple-DES in CBC mode.
        s.set_cipher(SMIME.Cipher("des_ede3_cbc"))
        # save data to buffer
        tmp = BIO.MemoryBuffer()
        p7.write_der(tmp)
        # encrypt
        p7 = s.encrypt(tmp, flags=SMIME.PKCS7_BINARY)
        out = BIO.MemoryBuffer()
        # write into a new buffer
        p7.write(out)
        return out.read()

    def _get_form_data(self, modify_existing_cart=False):
        """Creates a list of key,val to be sumbitted to PayPal."""
        submit = SortedDict()
        submit["business"] = self.settings["BUSINESS"]
        submit["currency_code"] = self.settings["CURRENCY_CODE"]
        submit["notify_url"] = self.settings["IPN_URL"]
        if self.settings.get("CHARSET"):
            submit["charset"] = self.settings["CHARSET"]
        if self.settings.get("RETURN_ADDRESS"):
            submit["return"] = self.settings["RETURN_ADDRESS"]
        if self.settings.get("RM"):
            submit["rm"] = self.settings["RM"]
        if self.settings.get("SHOPPING_URL"):
            submit["shopping_url"] = self.settings["SHOPPING_URL"]
        if self.settings.get("CANCEL_RETURN"):
            submit["cancel_return"] = self.settings["CANCEL_RETURN"]
        if self.settings.get("CBT"):
            submit["cbt"] = self.settings["CBT"]
        #TODO: eventually need to work out the terrible PayPal shipping stuff
        #      for now, we are saying "no shipping" and adding all shipping as
        #      a handling charge.
        if self.settings.get("NO_SHIPPING"):
            submit["no_shipping"] = self.settings["NO_SHIPPING"]
        else:
            submit["no_shipping"] = NO_SHIPPING["YES"]
        submit["handling_cart"] = self.cart.shipping
        if self.cart.tax:
            submit["tax_cart"] = self.cart.tax
        if self.cart.discount:
            submit['discount_amount_cart'] = self.cart.discount
        # Locale
        submit["lc"] = self.settings["LOCALE"]
        submit["invoice"] = self.cart.cart_uuid
        if len(self.cart.recurring_lineitems) > 1:
            self.log.error("Cannot have more than one subscription in one order for paypal.  Only processing the first one for %s", self.cart)
            return
        if len(self.cart.recurring_lineitems) > 0:
            item = self.cart.recurring_lineitems[0]
            submit["src"] = "1"
            submit["cmd"] = PAYMENT_CMD["SUBSCRIPTION"]
            submit["item_name"] = item.name
            submit["item_number"] = item.sku
            submit["no_note"] = NO_NOTE["YES"]
            submit["bn"] = "PP-SubscriptionsBF"
            if item.discount:
                submit['discount_amount'] = self.cart.discount
            if item.trial and item.recurring_start:
                raise GatewayError("PayPal can't have trial and delayed start")
            if item.recurring_start:
                delay = item.recurring_start - datetime.now()
                delay += timedelta(days=1) # Round up 1 day to PP shows right start
                if delay.days > 90:
                    raise GatewayError("PayPal doesn't support a delayed start of more than 90 days.")
                # Delayed subscription starts
                submit["a1"] = "0"
                submit["p1"] = delay.days
                submit["t1"] = "D"
            elif item.trial:
                # initial trial
                submit["a1"] = item.trial_price
                submit["p1"] = item.trial_length
                submit["t1"] = item.duration_unit
                if recur.recurdetails.trial_times > 1:
                    submit["a2"] = item.trial_price
                    submit["p2"] = item.trial_length
                    submit["t2"] = item.duration_unit
            if modify_existing_cart:
                # Messes up trial periods, so only use if no trial/delay
                submit["modify"] = "1"  # new or modify subscription
            # subscription price
            submit["a3"] = item.recurring_price
            submit["p3"] = item.duration
            submit["t3"] = item.duration_unit
            submit["srt"] = item.recurring_times
            if self.settings["REATTEMPT"]:
                reattempt = "1"
            else:
                reattempt = "0"
            submit["sra"] = reattempt
        else:
            submit["cmd"] = PAYMENT_CMD["CART"]
            submit["upload"] = "1"
            ix = 1
            for item in self.cart.one_time_lineitems:
                submit["item_name_%i" % ix] = item.name
                submit["amount_%i" % ix] = item.unit_price.quantize(Decimal(".01"))
                submit["quantity_%i" % ix] = item.quantity
                submit["on0_%i" % ix] = "SKU"
                submit["os0_%i" % ix] = item.sku
                if item.discount:
                    submit['discount_amount_' + ix] = self.cart.discount
                ix += 1
        if self.cart.bill_street1:
            submit["first_name"] = self.cart.bill_first_name
            submit["last_name"] = self.cart.bill_last_name
            submit["address1"] = self.cart.bill_street1
            submit["address2"] = self.cart.bill_street2
            submit["city"] = self.cart.bill_city
            submit["country"] = self.cart.bill_country
            submit["zip"] = self.cart.bill_postal_code
            submit["email"] = self.cart.bill_email
            submit["address_override"] = "0"
            # only U.S. abbreviations may be used here
            if self.cart.bill_country.lower() == "us" and len(self.cart.bill_state) == 2:
                submit["state"] = self.cart.bill_state
        return submit

    def _is_valid(self):
        """Return True if gateway is valid."""
        # Can't validate credentials with Paypal AFAIK
        return True

    def cancel_recurring(self):
        """Cancel recurring items with gateway. Returns a CancelResult."""
        alias = self.settings["BUSINESS"]
        url = "%s?cmd=%s&alias=%s" % (self.submit_url,
                                      PAYMENT_CMD["UNSUBSCRIBE"],
                                      self.settings["BUSINESS"])
        return CancelResult("url", url=url)

    def charge_recurring(self, grace_period=None):
        """This Paypal API doesn't support manually charging subscriptions."""
        pass

    def sanitize_clone(self):
        """Nothing to fix here."""
        pass

    def submit(self, collect_address=False, cart_settings_kwargs=None, modify_existing_cart=False):
        """Submit a cart to the gateway. Returns a SubmitResult."""
        self._update_with_cart_settings(cart_settings_kwargs)
        data = self._get_form_data(modify_existing_cart)
        if self.settings["ENCRYPT"]:
            data = {"encrypted": self._encrypt_data(data)}
        return SubmitResult("form", form_data={"action": self.submit_url,
                                               "fields": data})

    def refund_payment(self, payment, reason=None):
        """
        Refund the full amount of this payment
        """
        self.refund(payment.transaction_id, None, reason)

    def refund(self, transaction_id, amount=None, reason=None):
        self._update_with_cart_settings({'request': None})
        params = {}
        params['transactionid'] = transaction_id
        params['refundtype'] = 'Partial' if amount else 'Full'
        if amount:
            params['amt'] = Decimal(amount).quantize(Decimal('.01'))
        params['currencycode'] = self.settings['CURRENCY_CODE']
        if reason:
            params['note'] = reason

        response = self._do_nvp('RefundTransaction', params)

        return SubmitResult(None)

    def get_transaction_details(self, payment):
        params = {}
        params['transactionid'] = payment.transaction_id
        response = self._do_nvp('GetTransactionDetails', params)
        return response

    def get_recurring_payments_profile_details(self, subscription_id):
        params = {}
        params['profileid'] = subscription_id
        response = self._do_nvp('GetRecurringPaymentsProfileDetails', params)
        return response
