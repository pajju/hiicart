from django import forms


class PaymentFormBase(forms.Form):

    def __getitem__(self, key):
    	payment_fields = self._get_payment_fields()
        if key in payment_fields:
            key = payment_fields[key]
        return super(PaymentFormBase, self).__getitem__(key)

    def _get_payment_fields(self):
    	raise NotImplementedError()

	def set_result(self, result):
		"""
		Set result from payment gateway for form validation.
		"""
        raise NotImplementedError()