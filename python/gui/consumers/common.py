"""
Defines common functions used when communicating via websocket consumers
"""
import typing
import json
import inspect

import utilities

import maas_experiment.logging as common_logging

from maas_experiment import application_values

def inner_data_is_wrapper(possible_wrapper: dict) -> bool:
    """
    Determines whether the passed dictionary is just a wrapper for a dictionary named 'data'

    Args:
        possible_wrapper: A possible dictionary that just contains another dictionary named 'data'

    Returns:
        Whether the passed dictionary is just a wrapper for a dictionary named 'data'
    """
    return possible_wrapper is not None \
           and isinstance(possible_wrapper, dict) \
           and 'data' in possible_wrapper \
           and isinstance(possible_wrapper['data'], dict) \
           and len(possible_wrapper['data']) == 1 \
           and 'data' in possible_wrapper['data']


def make_message(
    event: str = None,
    response_type: str = None,
    data: typing.Union[str, dict] = None,
    logger: common_logging.ConfiguredLogger = None
) -> dict:
    """
    creates a message to communicate to either a socket or channel

    Args:
        event: Why the message was sent
        response_type: What type of response this is
        data: The data to send
        logger: A logger used to store diagnositic and error data if needed

    Returns:
        A message with useful data to communicate
    """
    if logger is None:
        logger = common_logging.ConfiguredLogger()

    # Not much can be done with bytes, so go ahead and convert data to a string
    if data and isinstance(data, bytes):
        data = data.decode()

    # If the data might be a json string, try to parse it. If it doesn't parse, we'll just consider it as the
    # basic payload to be communicated. An exception here is ok.
    if utilities.string_might_be_json(data):
        try:
            data = json.loads(data)
        except Exception as load_exception:
            logger.error(
                f"[{inspect.currentframe().f_code.co_name}] The passed data was a non-json string; "
                f"it can't be converted to JSON for further decomposition for a websocket response",
                load_exception
            )

    message_time = utilities.now().strftime(application_values.COMMON_DATETIME_FORMAT)

    # If the data is a dict, its contents can be rearranged to properly fit the message format to be sent
    # (such as event data floating to the top instead of being buried below)
    if isinstance(data, dict):
        use_inner_data = False

        # Make sure the contained data can actually be communicated
        data = utilities.make_message_serializable(data)

        # If this dictionary has a 'data' member that ALSO has a 'data' member, promote the first data member and tell
        # the logic to use the newly promoted inner-inner 'data' member for investigation
        if 'data' in data and isinstance(data['data'], typing.Container) and 'data' in data['data']:
            if utilities.string_might_be_json(data['data']):
                try:
                    contained_data = json.loads(data.pop('data'))
                except Exception as loads_exception:
                    logger.error(f"'{str(data)}' didn't parse into a dict so we're using it raw", loads_exception)
                    contained_data = data.pop('data')
            else:
                contained_data = data.pop('data')

            use_inner_data = True
        else:
            contained_data = data

        # Check to see if 'event' has been defined within the passed data or the inner data
        if 'event' in contained_data and contained_data['event']:
            event = contained_data.pop('event')
        elif 'event' in data and data['event']:
            event = data.pop('event')

        # Check to see if 'type' has been defined within the passed data or the inner data
        if 'type' in contained_data and contained_data['type']:
            response_type = contained_data.pop('type')
        elif 'type' in data and data['type']:
            response_type = data.pop('type')

        # Check to see if 'response_type' has been defined within the passed data or inner data
        if 'response_type' in contained_data and contained_data['response_type']:
            response_type = contained_data.pop('response_type')
        elif 'response_type' in data and data['response_type']:
            response_type = data.pop('response_type')

        # Check to see if 'time' has been defined within the passed data or inner data
        if 'time' in contained_data and contained_data['time']:
            message_time = contained_data.pop('time')
        elif 'time' in data and data['time']:
            message_time = data.pop('time')

        # Now that important values have been pulled out of the top level 'data' dictionary,
        # promote the inner level if its used
        data = contained_data['data'] if use_inner_data else contained_data

        # Try to convert data to json one last time
        if utilities.string_might_be_json(data):
            try:
                data = json.loads(data)
            except Exception as loads_exception:
                logger.error(f"Could not deserialize data", loads_exception)
    elif isinstance(data, str):
        data = {
            "message": data
        }

    # Event can't be null, so set it to something
    if event is None:
        event = "send_message"

    # If no response type was given, go ahead and set it to something
    if not response_type:
        response_type = "send_message"

    if isinstance(data, dict):
        # While the data dictionary just looks like `{"data": {"data": {...}}}`, bring the actual data up a level
        while isinstance(data.get("data"), dict) and len(data) == 1:
            data = data.get('data')

        # Again, promote inner 'data' instances if it just looks like the inner value is just another dict named 'data'
        # Will convert:
        #    data = {"val1": 1, "val2": 2, "data": {"data": [1, 2, 3]}}
        # To
        #    data = {"val1": 1, "val2": 2, "data": [1, 2, 3]}
        # The following will not be changed:
        #    data = {"val1": 1, "val2": 2, "data": {"data": [1, 2, 3], "other_data": 8}}
        while inner_data_is_wrapper(data.get('data')):
            data['data'] = data.get('data').get('data')

    # Create a basic response detailing what event caused the message to be sent, the general gist of the message,
    # when it was sent, and data as a basic payload to be communicated
    message = {
        "event": event,
        "type": response_type,
        'time': message_time,
        "data": data
    }

    # Make sure that only data that may be transmitted is within the message (i.e. nothing like binary data)
    message = utilities.make_message_serializable(message)

    return message


def make_websocket_message(
    event: str = None,
    response_type: str = None,
    data: typing.Union[str, dict] = None,
    logger: common_logging.ConfiguredLogger = None
) -> str:
    """
    Formats response data into a form that is easy for the other end of the socket to digest

    Args:
        event: Why the message was sent
        response_type: What type of response this is
        data: The data to send
        logger: A logger used to store diagnostic and error data if needed

    Returns:
        A JSON string containing the data to be sent along the socket
    """
    return json.dumps(make_message(event, response_type, data, logger), indent=4)




def make_key(*args) -> str:
    """
    Forms a key based on all passed in items

    Given `key_separator()` => '--', `make_key('one', 'two-five', 'three--four')` becomes 'one--two-five--three--four'

    Args:
        *args: Elements with that make up unique sections of a key

    Returns:

    """
    parts = list()
    separator = application_values.KEY_SEPARATOR

    for arg in args:
        if arg:
            parts.extend(
                [
                    str(part).strip()
                    for part in str(arg).strip().strip(separator).split(separator)
                    if part and str(part).strip()
                ]
            )

    return separator.join(parts)


def get_group_key(channel_name: str) -> str:
    """
    Gets the name of a channel to publish to for an evaluation

    Args:
        channel_name: The name of the given channel that needs a formal key

    Returns:
        The name of the channel to publish to for this evaluation
    """
    separator = application_values.KEY_SEPARATOR
    prefix = application_values.APPLICATION_PREFIX

    args = channel_name.strip().strip(separator).split(separator)

    if args[0] != prefix:
        args.insert(0, prefix)

    channel_id = make_key(*args)

    if not channel_id.endswith(separator + "COMMUNICATION"):
        channel_id = make_key(channel_id, "COMMUNICATION")

    return channel_id
