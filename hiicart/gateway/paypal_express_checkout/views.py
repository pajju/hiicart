from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_view_exempt
from hiicart.gateway.paypal_express_checkout.gateway import PaypalExpressCheckoutGateway
from hiicart.gateway.paypal_express_checkout.ipn import PaypalExpressCheckoutIPN
from hiicart.gateway.paypal.views import _base_paypal_ipn_listener
from hiicart.utils import format_exceptions, cart_by_uuid

@never_cache
def confirm_details(request, cart_uuid):
    token = request.session.get('hiicart_paypal_express_token')
    cart = cart_by_uuid(cart_uuid)
    if cart:
        gateway = PaypalExpressCheckoutGateway(cart)

        details = gateway.get_details(token)

@never_cache
def finalize(request):
    data = request.GET
    token = data['token']
    payerid = data['payerid']

    cart = cart_by_uuid(cart_uuid)
    if cart:
        gateway = PaypalExpressCheckoutGateway(cart)

        gateway.finalize(token, payerid)

@csrf_view_exempt
@format_exceptions
@never_cache
def ipn(request):
    return _base_paypal_ipn(request, PaypalExpressCheckoutIPN)
