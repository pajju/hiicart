import hiicart.gateway.paypal_express.views

from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'get_details/?$',                     'hiicart.gateway.paypal_express.views.get_details'),
    (r'finalize/?$',                            'hiicart.gateway.paypal_express.views.finalize'),
    (r'ipn/?$',                                 'hiicart.gateway.paypal_express.views.ipn'),
)
