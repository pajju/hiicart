import hiicart.gateway.paypal_express_checkout.views

from django.con.urls.defaults import *

urlpatterns = patterns('',
    (r'confirm_details/?$',                     'hiicart.gateway.paypal_express_checkout.views.confirm_details'),
    (r'finalize/?$',                            'hiicart.gateway.paypal_express_checkout.views.finalize'),
    (r'ipn/?$',                                 'hiicart.gateway.paypal_express_checkout.views.ipn'),
)
