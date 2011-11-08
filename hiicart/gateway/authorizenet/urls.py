import hiicart.gateway.authorizenet.views

from django.conf.urls.defaults import *

urlpatterns = patterns('',  
    (r'ipn/?$',                                    'hiicart.gateway.authorizenet.views.ipn'),
)
