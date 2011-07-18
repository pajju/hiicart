import braintree

from django import forms
from django.forms.util import ErrorDict

class PaymentForm(forms.Form):
	"""
	Braintree payment form.
	"""
	tr_data = forms.CharField(widget=forms.HiddenInput)
	transaction__credit_card__cardholder_name = forms.CharField()
	transaction__credit_card__number = forms.CharField()
	transaction__credit_card__cvv = forms.CharField(min_length=3, max_length=4)
	transaction__credit_card__expiration_month = forms.CharField(min_length=1, max_length=2)
	transaction__credit_card__expiration_year = forms.CharField(min_length=4, max_length=4)

	def __init__(self, *args, **kwargs):
		tr_data = kwargs.pop('tr_data', '')
		super(PaymentForm, self).__init__(*args, **kwargs)

	def set_transaction(self, tr_data):
		if self.is_bound:
			self.data['tr_data'] = tr_data
		else:
			self.fields['tr_data'].initial = tr_data

	def set_result(self, result):
		"""
		Use the results of the gateway payment confirmation to set 
		validation errors on the form.
		"""
		self._errors = ErrorDict()
		self.is_bound = True
		if not result.success:
			for name, error in result.errors.items():
				if name == 'cardholder_name':
					name = 'transaction__credit_card__cardholder_name'
				elif name == 'number':
					name = 'transaction__credit_card__number'
				elif name == 'cvv':
					name = 'transaction__credit_card__cvv'
				elif name == 'expiration_month':
					name = 'transaction__credit_card__expiration_month'
				elif name == 'expiration_year':
					name = 'transaction__credit_card__expiration_year'
				elif name == 'non_field_errors':
					name = forms.forms.NON_FIELD_ERRORS
				self._errors[name] = self.error_class([error])

	@property
	def action(self):
		"""
		Action to post the form to.
		"""
		return braintree.TransparentRedirect.url()