import logging
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_view_exempt
from hiicart.gateway.base import GatewayError
from hiicart.gateway.authorizenet.ipn import AuthorizeNetIPN
from hiicart.utils import format_exceptions, cart_by_uuid
from urllib import unquote_plus
from urlparse import parse_qs


log = logging.getLogger("hiicart.gateway.authorizenet")


def _find_cart(data):
    return cart_by_uuid(data['cart_id'])


@csrf_view_exempt
@format_exceptions
@never_cache
def ipn(request):
    """
    Authorize.net Payment Notification
    """
    if request.method != "POST":
        return HttpResponse("Requests must be POSTed")
    data = request.POST.copy()
    print request.raw_post_data
    for key in data:
        print key, data[key]
    log.info("IPN Notification received from Authorize.net: %s" % data)
    try:
        log.info("IPN Notification received from Authorize.net (raw): %s" % request.raw_post_data)
    except:
        pass
    cart = _find_cart(data)
    if not cart:
        raise GatewayError('Authorize.net gateway: Unknown transaction')
    handler = AuthorizeNetIPN(cart)
    if not handler.confirm_ipn_data(data):
        log.error("Authorize.net IPN Confirmation Failed.")
        raise GatewayError("Authorize.net IPN Confirmation Failed.")
    if data['x_response_code'] == 1:  # Approved
        handler.accept_payment(data)
    elif data['x_response_code'] == 2:  # Declined
        pass
    elif data['x_response_code'] == 3:  # Error
        pass
    elif data['x_response_code'] == 4:  # Held
        pass
    return HttpResponse("<html><head><script language=\"javascript\">window.location=\"%s\";</script></head><body><noscript><meta http-equiv=\"refresh\" content=\"1;url=%s\"></noscript></body></html>" % (data['return_url'], data['return_url']))
