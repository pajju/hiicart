import braintree

from datetime import datetime
from django import forms
from django.forms.util import ErrorDict

EXPIRATION_MONTH_CHOICES = [(i, "%02d" % i) for i in range(1, 13)]
EXPIRATION_YEAR_CHOICES = range(datetime.now().year, datetime.now().year + 10)

class _BasePaymentForm(object):
    """
    Braintree payment form.

    Before displaying the form, make sure to call set_transaction with the
    result of BraintreeGateway.start_transaction to set required transaction
    fields.

    To validate, pass the result of BraintreeGateway.confirm_payment to
    set_result. This will set any errors to the appropriate field.
    """
    def __init__(self, *args, **kwargs):
        tr_data = kwargs.pop('tr_data', '')
        super(_BasePaymentForm, self).__init__(*args, **kwargs)

    def set_transaction(self, tr_data):
        if self.is_bound:
            self.data['tr_data'] = tr_data
        else:
            self.fields['tr_data'].initial = tr_data

    def hidden_fields(self):
        """
        Get hidden fields required for this form.
        """
        return [self['tr_data']]

    @property
    def action(self):
        """
        Action to post the form to.
        """
        return braintree.TransparentRedirect.url()

    def set_result(self, result):
        """
        Use the results of the gateway payment confirmation to set
        validation errors on the form.
        """
        self._errors = ErrorDict()
        self.is_bound = True
        prefix = 'transaction__' if self.__class__.__name__ == 'PaymentForm' else 'customer__'
        if not result.success:
            for name, error in result.errors.items():
                if name == 'cardholder_name':
                    name = prefix+'credit_card__cardholder_name'
                elif name == 'number':
                    name = prefix+'credit_card__number'
                elif name == 'cvv':
                    name = prefix+'credit_card__cvv'
                elif name == 'expiration_month':
                    name = prefix+'credit_card__expiration_month'
                elif name == 'expiration_year':
                    name = prefix+'credit_card__expiration_year'
                elif name == 'non_field_errors':
                    name = forms.forms.NON_FIELD_ERRORS
                self._errors[name] = self.error_class([error])


    def __getattr__(self, name):
        prefix = 'transaction__' if self.__class__.__name__ == 'PaymentForm' else 'customer__'
        if 'billing' in name and prefix == 'customer__':
            prefix = 'customer__credit_card__'
        try:
            return self[prefix+name]
        except KeyError:
            return object.__getattribute__(self, name)


def make_form(is_recurring=False):
    prefix = 'customer__' if is_recurring else 'transaction__'
    fields = {
        'tr_data': forms.CharField(widget=forms.HiddenInput),
        prefix+'credit_card__cardholder_name': forms.CharField(),
        prefix+'credit_card__number': forms.CharField(),
        prefix+'credit_card__cvv': forms.CharField(min_length=3, max_length=4),
        prefix+'credit_card__expiration_month': forms.ChoiceField(choices=EXPIRATION_MONTH_CHOICES, initial=datetime.now().month),
        prefix+'credit_card__expiration_year': forms.ChoiceField(choices=EXPIRATION_YEAR_CHOICES),
    }

    if prefix == 'transaction__':
        # Customers don't have shipping addresses, transactions do
        fields.update({
            prefix+'shipping__first_name': forms.CharField(max_length=255),
            prefix+'shipping__last_name': forms.CharField(max_length=255),
            prefix+'shipping__street_address': forms.CharField(max_length=80),
            prefix+'shipping__extended_address': forms.CharField(max_length=80),
            prefix+'shipping__locality': forms.CharField(max_length=50),
            prefix+'shipping__region': forms.CharField(max_length=50),
            prefix+'shipping__postal_code': forms.CharField(max_length=30),
            prefix+'shipping__country_code_alpha2': forms.CharField(max_length=2),
        })

    if prefix == 'customer__':
        prefix = 'customer__credit_card__'
    fields.update({
        prefix+'billing__first_name': forms.CharField(max_length=255),
        prefix+'billing__last_name': forms.CharField(max_length=255),
        prefix+'billing__street_address': forms.CharField(max_length=80),
        prefix+'billing__extended_address': forms.CharField(max_length=80),
        prefix+'billing__locality': forms.CharField(max_length=50),
        prefix+'billing__region': forms.CharField(max_length=50),
        prefix+'billing__postal_code': forms.CharField(max_length=30),
        prefix+'billing__country_code_alpha2': forms.CharField(max_length=2),
    })
        
    typename = 'CustomerForm' if is_recurring else 'PaymentForm'
    return type(typename, (_BasePaymentForm, forms.BaseForm,), {'base_fields': fields})

