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
    minutes_str = "00:{}:00".format(minutes)
    r = set_value_for_date(cur_date, ATTR_MAP["latency"], minutes_str)
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

    prev_bedtime = get_value_on_date(cur_date, ATTR_MAP["bedtime"]) 

    if not prev_bedtime:
        response_str = "Sorry, it looks like you haven't set a bedtime yet."
        return alexa.create_response(response_str, end_session=True)

    prev_bedtime = create_datetime_from_time(prev_bedtime)

    latency = int((cur_date - prev_bedtime).total_seconds()/60)
    latency_str = "00:{}:00".format(latency)

    set_value_for_date(cur_date, ATTR_MAP["latency"], latency_str)

    response_str = "OK Michael, I updated your sleep latency to {} minutes".format(latency)
    return alexa.create_response(response_str, end_session=True)


@alexa.intent_handler("GetTimeSleptIntent")
def get_time_slept_intent(request):
    cur_date = get_cur_date() - timedelta(days=1)

    bedtime = get_value_on_date(cur_date, ATTR_MAP["bedtime"])
    waketime = get_value_on_date(cur_date, ATTR_MAP["waketime"])
    latency = get_value_on_date(cur_date, ATTR_MAP["latency"])

    if not bedtime:
        return alexa.create_response("Sorry, looks like you didn't set a bedtime yesterday.")

    if not waketime:
        return alexa.create_response("Sorry, looks like you didn't wake up yesterday.")

    if not latency:
        latency = timedelta() # In case we didn't record latency
    else:
        h, m, s = map(int, latency.split(":"))
        latency = timedelta(hours=h, minutes=m) 

    #If bedtime is before midnight, subtract an extra day
    if bedtime[-2:] == "PM":
        bedtime = create_datetime_from_time(bedtime, cur_date - timedelta(days=1))
    else:
        bedtime = create_datetime_from_time(bedtime, cur_date)
    bedtime += latency

    waketime = create_datetime_from_time(waketime, cur_date)
    duration = waketime - bedtime
    hours = int(duration.total_seconds() / 3600)
    minutes = int((duration.total_seconds() % 3600)/60)

    response_str = "You slept {} hours and {} minutes last night, Michael.".format(hours, minutes)
    return alexa.create_response(response_str, end_session=True)



# TODO: Factor some of this out to a utilities class
def create_datetime_from_time(date_str, desired_date):
    """Unparsed a time and creates a datetime of the object on a given date, in the current TZ
    """

    dt = datetime.strptime(date_str, TIME_FMT)
    dt = dt.replace(year=desired_date.year, month=desired_date.month, day=desired_date.day)
    return CURRENT_TZ.localize(dt)


def get_value_on_date(d, attribute):
    """Returns the raw value of an attribute on a given day (extracted from the returned JSON),
       or none if it doesn't exist.
    """

    date_str = d.strftime(DATE_FMT)
    endpoint = make_endpoint(date_str, attribute)
    value = requests.get(endpoint)
    try:
        return value.json()[attribute]
    except:
        return None


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

