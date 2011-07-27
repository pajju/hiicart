from datetime import datetime
from django import forms
from django.forms.util import ErrorDict

PAYMENT_FIELDS = {'credit_card_number': 'x_card_num',
                  'credit_card_cvv': 'x_card_code',
                  'credit_card_exp_date': 'x_exp_date',
                  'billing_first_name': 'x_first_name',
                  'billing_last_name': 'x_last_name',
                  'billing_street': 'x_address',
                  'billing_city': 'x_city',
                  'billing_state': 'x_state',
                  'billing_zipcode': 'x_zip',
                  'billing_country': 'x_country',
                  'shipping_first_name': 'x_ship_to_first_name',
                  'shipping_last_name': 'x_ship_to_last_name',
                  'shipping_street': 'x_ship_to_address',
                  'shipping_city': 'x_ship_to_city',
                  'shipping_state': 'x_ship_to_state',
                  'shipping_zipcode': 'x_ship_to_zip',
                  'shipping_country': 'x_ship_to_country'}

EXPIRATION_MONTH_CHOICES = [(i, "%02d" % i) for i in range(1, 13)]
EXPIRATION_YEAR_CHOICES = range(datetime.now().year, datetime.now().year + 10)


class PaymentForm(forms.Form):
    """
    Authorize.net payment form.
    """
    return_url = forms.CharField()
    cart_id = forms.CharField()
    x_invoice_num = forms.CharField()
    x_amount = forms.CharField()
    x_fp_sequence = forms.CharField()
    x_fp_timestamp = forms.CharField()
    x_fp_hash = forms.CharField()
    x_relay_response = forms.CharField()
    x_relay_url = forms.CharField()
    x_login = forms.CharField()
    x_method = forms.CharField()
    x_type = forms.CharField()
    x_test_request = forms.CharField()
    x_version = forms.CharField()
    x_card_num = forms.CharField()
    x_card_code = forms.CharField(min_length=3, max_length=4)
    x_exp_date = forms.CharField()
    x_first_name = forms.CharField(max_length=255)
    x_last_name = forms.CharField(max_length=255)
    x_address = forms.CharField(max_length=80)
    x_city = forms.CharField(max_length=50)
    x_state = forms.CharField(max_length=50)
    x_zip = forms.CharField(max_length=30)
    x_country = forms.CharField(max_length=2)
    x_ship_to_first_name = forms.CharField(max_length=255)
    x_ship_to_last_name = forms.CharField(max_length=255)
    x_ship_to_address = forms.CharField(max_length=80)
    x_ship_to_city = forms.CharField(max_length=50)
    x_ship_to_state = forms.CharField(max_length=50)
    x_ship_to_zip = forms.CharField(max_length=30)
    x_ship_to_country = forms.CharField(max_length=2)

    def __init__(self, *args, **kwargs):
        super(PaymentForm, self).__init__(*args, **kwargs)

    def __getitem__(self, key):
        if key in PAYMENT_FIELDS:
            key = PAYMENT_FIELDS[key]
        return super(PaymentForm, self).__getitem__(key)

    def set_transaction(self, data):
        self._submit_url = data['submit_url']
        for key in data:
            if key[:2] == 'x_' or key == "return_url" or key == "cart_id":
                if self.is_bound:
                    self.data[key] = data[key]
                else:
                    self.fields[key].initial = data[key]

    def set_result(self, result):
        """
        Use the results of the gateway payment confirmation to set
        validation errors on the form.
        """
        self._errors = ErrorDict()
        self.is_bound = True
        if not result.success:
            self._errors[forms.forms.NON_FIELD_ERRORS] = self.error_class([result.errors])

    def hidden_fields(self):
        """
        Get hidden fields required for this form.
        """
        return [self['return_url'],
                self['cart_id'],
                self['x_invoice_num'],
                self['x_amount'],
                self['x_fp_hash'],
                self['x_fp_sequence'],
                self['x_relay_response'],
                self['x_relay_url'],
                self['x_login'],
                self['x_version'],
                self['x_fp_timestamp'],
                self['x_method'],
                self['x_type'],
                self['x_test_request']]

    @property
    def action(self):
        """
        Action to post the form to.
        """
        return self._submit_url
