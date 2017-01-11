from ask import alexa
from datetime import date, timedelta, datetime
from pytz import timezone
import pytz
import requests


LOGS_ENDPOINT = "https://thawing-basin-65008.herokuapp.com/logs/"
DATE_FMT = "%m-%d-%Y"
TIME_FMT = "%I:%M:00 %p"
CURRENT_TZ = timezone("US/Pacific") # Change this when I go back to SWAT
ATTR_MAP = {
            "latency": "Sleep Latency",
            "bedtime": "Bedtime",
            "waketime": "Wakeup"
            }


@alexa.default_handler()
def default_handler(request):
    """ The default handler gets invoked if no handler is set for a request """
    return alexa.create_response(message="Say: I'm going to bed, or, I'm awake.")


@alexa.request_handler("LaunchRequest")
def launch_request_handler(request):
    return alexa.create_response(message="Welcome to Life Log")


@alexa.request_handler("SessionEndedRequest")
def session_ended_request_handler(request):
    return alexa.create_response(message="Goodbye!")


@alexa.intent_handler('SetBedtimeIntent')
def set_bedtime_intent_handler(request):
    """ Tell Alexa when you went to bed. 
    """

    # TODO: This guy should clear out the sleep latency for the day when it's set 
    cur_date = get_cur_date()

    # If bedtime is AM, set date to be previous day
    if cur_date.hour < 12:
        cur_date = cur_date - timedelta(days=1)
    bedtime = cur_date.strftime(TIME_FMT)

    r = set_value_for_date(cur_date, ATTR_MAP["bedtime"], bedtime)
    response_str = "OK, I logged your bedtime as {}. Goodnight Michael!".format(
                    cur_date.strftime("%I %M %p"))

    return alexa.create_response(response_str, end_session=True) 


@alexa.intent_handler("SetWaketimeIntent")
def set_waketime_intent_handler(request):
    """ Tell Alexa when you woke up. 
    """

    cur_date = get_cur_date() - timedelta(days=1)
    wake_str = cur_date.strftime(TIME_FMT)
    r = set_value_for_date(cur_date, ATTR_MAP["waketime"], wake_str)
    # TODO Unhappy path
    response_str = "Good morning Michael! I logged your wakeup time as {}. Have a great day!".format(
                    cur_date.strftime("%I %M %p"))

    return alexa.create_response(response_str, end_session=True) 


@alexa.intent_handler("SetLatencyIntent")
def set_latency_intent(request):
    """Tell Alexa how long it took you to fall asleep.
    Expects to be called the day after you went to bed. 
    """

    cur_date = get_cur_date() - timedelta(days=1)
    minutes = request.slots["Minutes"]
    r = set_value_for_date(cur_date, ATTR_MAP["latency"], minutes)
    # TODO: Unhappy path
    response_str = "OK, I logged your sleep latency as {} minutes.".format(
                    minutes)

    return alexa.create_response(response_str, end_session=True) 


@alexa.intent_handler("UpdateLatencyIntent")
def update_latency_intent(request):
    """Sets the sleep latency based on the current time and the previously logged bedtime. 
    """
    cur_date = get_cur_date()

    if cur_date.hour < 12:
        cur_date = cur_date - timedelta(days=1)

    prev_bedtime = get_value_for_date(cur_date, ATTR_MAP["bedtime"]) 
    prev_bedtime = prev_bedtime.json()[ATTR_MAP["bedtime"]]

    if not prev_bedtime:
        response_str = "Sorry, it looks like you haven't set a bedtime yet."
        return alexa.create_response(response_str, end_session=True)

    # TODO: Refactor this goopy bit
    prev_bedtime = datetime.strptime(prev_bedtime, TIME_FMT)
    prev_bedtime = prev_bedtime.replace(year=cur_date.year, month=cur_date.month,
                                        day=cur_date.day)
    prev_bedtime = CURRENT_TZ.localize(prev_bedtime)

    latency = int((cur_date - prev_bedtime).total_seconds()/60)
    set_value_for_date(cur_date, ATTR_MAP["latency"], latency)

    response_str = "OK Michael, I updated your sleep latency to {} minutes".format(latency)
    return alexa.create_response(response_str, end_session=True)

def get_value_for_date(d, attribute):
    date_str = d.strftime(DATE_FMT)
    endpoint = make_endpoint(date_str, attribute)
    return requests.get(endpoint)

def set_value_for_date(d, attribute, value):
    """POSTS a value for a given date. 
    """
    date_str = d.strftime(DATE_FMT)
    payload = {"value": value}
    endpoint = make_endpoint(date_str, attribute)
    return requests.post(endpoint, data=payload)

def make_endpoint(date_str, attribute):
    return LOGS_ENDPOINT + "{}/{}".format(date_str, attribute)


def get_cur_date(): 
    return CURRENT_TZ.localize(datetime.now())
