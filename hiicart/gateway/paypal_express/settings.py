"""Settings for Paypal Express Checkout gateway

**Required settings:**
 * *API_USERNAME*
 * *API_PASSWORD*
 * *API_SIGNATURE*
 * *API_VERSION*
 * *RETURN_URL*
 * *CANCEL_URL*

**Optional settings:**
 * *CURRENCY_CODE* -- Currency for transactions [default: USD]
 * *IPN_URL* -- URL to send IPN messages. [defualt: None (uses acct defaults)]
 * *LOCALE* -- Seller's locale. [default: US]

"""

SETTINGS = {
    "CURRENCY_CODE" : "USD",
    "LOCALE" : "US",
    "IPN_URL" : "",
    "API_VERSION" : "76.0",
    }
