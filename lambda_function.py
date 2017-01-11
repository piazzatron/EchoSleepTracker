from ask import alexa
from datetime import date, timedelta, datetime
from pytz import timezone
import pytz
import requests
import voice_handlers

def lambda_handler(request_obj, context=None):
    metadata = {} 
    return alexa.route_request(request_obj, metadata)
