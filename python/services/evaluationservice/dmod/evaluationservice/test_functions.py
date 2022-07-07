#!/usr/bin/env python3
import typing
import math
import json

from time import sleep

import redis


DELAY_SECONDS = 5


def multiply(channel_name, *numbers, **kwargs):
    connection = redis.Redis()

    sleep(DELAY_SECONDS)

    issues = list()

    if kwargs:
        message = f"The following cannot be factored into multiplication: {kwargs}"
        connection.publish(channel_name, f"WARNING: {message}")
        issues.append(message)

    value = None

    for number in numbers:
        if value is None:
            value = number
        else:
            value *= number

    sleep(DELAY_SECONDS)

    response = {
        "event": "multiply",
        "data": {
            "value": value,
            "issues": issues
        }
    }

    connection.publish(channel_name, "Generated data from test_functions.multiply:")
    connection.publish(channel_name, json.dumps(response))

    sleep(DELAY_SECONDS)

    return response


async def async_multiply(channel_name, *numbers, **kwargs):
    connection = redis.Redis()
    connection.publish(channel_name, "[test_functions.async_multiply] Calling the multiply function")
    result = multiply(channel_name, *numbers, **kwargs)
    connection.publish(channel_name, "[test_function.async_multiply] The multiply function has completed")
    return json.dumps(result, indent=4)


def add(channel_name, *numbers, **kwargs):
    connection = redis.Redis()

    sleep(DELAY_SECONDS)

    issues = list()

    if kwargs:
        message = f"The following cannot be factored into addition: {kwargs}"
        connection.publish(channel_name, f"WARNING: {message}")
        issues.append(message)

    value = sum(numbers)

    sleep(DELAY_SECONDS)

    response = {
        "event": "add",
        "data": {
            "value": value,
            "issues": issues
        }
    }

    connection.publish(channel_name, "Generated data from test_functions.add:")
    connection.publish(channel_name, json.dumps(response))

    sleep(DELAY_SECONDS)

    return response


async def async_add(channel_name, *numbers, **kwargs):
    connection = redis.Redis()
    connection.publish(channel_name, "[test_functions.async_add] Calling the add function")
    result = add(channel_name, *numbers, **kwargs)
    connection.publish(channel_name, "[test_function.async_add] The add function has completed")
    return json.dumps(result, indent=4)


def subtract(channel_name, *numbers, **kwargs):
    connection = redis.Redis()

    sleep(DELAY_SECONDS)

    issues = list()

    if kwargs:
        message = f"The following cannot be factored into subtraction: {kwargs}"
        connection.publish(channel_name, f"WARNING: {message}")
        issues.append(message)

    value = None

    for number in numbers:
        if value is None:
            value = number
        else:
            value -= number

    sleep(DELAY_SECONDS)

    response = {
        "value": value,
        "issues": issues
    }

    connection.publish(channel_name, "Generated data from test_functions.subtract:")
    connection.publish(channel_name, json.dumps(response))

    sleep(DELAY_SECONDS)

    return response


async def async_subtract(channel_name, *numbers, **kwargs):
    connection = redis.Redis()
    connection.publish(channel_name, "[test_functions.async_subtract] Calling the subtract function")
    result = subtract(channel_name, *numbers, **kwargs)
    connection.publish(channel_name, "[test_function.async_subtract] The subtract function has completed")
    return json.dumps(result, indent=4)


def echo(channel_name, *message: str, **kwargs):
    print("[test_functions.echo] Entered the echo function - connecting to redis")
    connection = redis.Redis()

    connection.publish(channel_name, "In the echo function; sleeping to simulate a delay")

    print("[test_functions.echo] sleeping to simulate a delay")
    sleep(DELAY_SECONDS)

    echo_message = ""

    if message:
        echo_message += " ".join(message)

    if kwargs:
        echo_message += f" {json.dumps(kwargs)}"

    response = {
        "event": "echo",
        "data": {
            "value": echo_message,
            "issues": []
        }
    }

    connection.publish(channel_name, "Generated data from test_functions.echo:")
    connection.publish(channel_name, json.dumps(response))

    print("[test_functions.echo] Sleeping again to simulate a delay")
    sleep(DELAY_SECONDS)

    return response


async def async_echo(channel_name, *message: str, **kwargs):
    connection = redis.Redis()
    connection.publish(channel_name, "[test_functions.async_echo] Calling the echo function")
    result = echo(channel_name, *message, **kwargs)
    connection.publish(channel_name, "[test_function.async_echo] The echo function has completed")
    return json.dumps(result, indent=4)


def concat(channel_name, *args, **kwargs):
    connection = redis.Redis()

    sleep(DELAY_SECONDS)

    message = "".join(args)

    if kwargs:
        message += f" {json.dumps(kwargs)}"

    response = {
        "event": "concat",
        "data": {
            "value": message,
            "issues": []
        }
    }

    connection.publish(channel_name, "Generated data from test_functions.concat:")
    connection.publish(channel_name, json.dumps(response))

    sleep(DELAY_SECONDS)

    return response

async def async_concat(channel_name, *args, **kwargs):
    connection = redis.Redis()
    connection.publish(channel_name, "[test_functions.async_concat] Calling the concat function")
    result = concat(channel_name, *args, **kwargs)
    connection.publish(channel_name, "[test_function.async_concat] The concat function has completed")
    return json.dumps(result, indent=4)
