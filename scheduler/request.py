import sys
import os
import time
import json, ast
import docker
from itertools import chain
from pprint import pprint as pp
from redis import Redis, WatchError

## local imports for unittest
import scheduler.utils.keynamehelper as keynamehelper
import scheduler.generate as generate

## local imports for production run
# import utils.keynamehelper as keynamehelper
# import generate as generate

redis = None

class Request:
    def __init__(self, user_id, cpus, mem):
        # self.user_id = user_id
        self.user_id = "shengting.cui"
        self.cpus = cpus
        self.mem = mem

    def create_request_and_validate(self):
        """Class function create_request_and_validate(self)"""
        print("\n==Test 1: create a request based on user input parameters")

        # Resource available
        print("== First request")
        # requestor = "shengting.cui"
        user_id = self.user_id
        print("user_id = ", self.user_id)
        requestor = self.user_id
        print("requestor id = ", requestor)
        # resource_requested = "Node-0001"
        cpus = self.cpus
        print("cpus = ", self.cpus)
        mem = self.mem
        print("mem = ", self.mem)
        req_set_key = keynamehelper.create_key_name(user_id)
        p = redis.pipeline()
        try:
            req_id = generate.order_id()
            request = {'req_id': req_id, 'user_id': user_id,
                       'cpus': cpus, 'mem': mem,
                       'ts': int(time.time())}
            # req_key consists of "job_request:req_id"
            req_key = keynamehelper.create_key_name(requestor, req_id)
            print(req_key)
            p.hmset(req_key, request)
        except:
            print("user request not created")
        redis.sadd(req_set_key, request['req_id'])

        # check_availability_and_schedule(requestor, resource_requested, req_cpus, req_mem, req_time)
        # check_availability_and_schedule(requestor, resources, req_cpus, req_mem, req_time)
        # print_resource_details(resources)

        # call this function when user enters a username
    def create_user_from_username(self):
        """Get user id from the user input, store in database"""
        print("\nIn create_user_from_username(): user_id = ", user_id)
        try:
            c_key = keynamehelper.create_key_name("user", user_id)
            print(c_key)
            user = {'user_id': user_id}
            redis.hmset(c_key, user)
        except:
            print("user not created")

    # def create_users(user_array):
    #     """Create user keys from the array of passed user info"""
    #     for user in user_array:
    #         c_key = keynamehelper.create_key_name("user", user['id'])
    #         # print("In create_customers: c_key = ", c_key)
    #         redis.hmset(c_key, user)


def user_request_input():
    user_list = []
    while True:
        username = input("Enter username (or Enter to continue): ")
        if not username:
            break
        print("Your input:", username)
        user_list.append(username)

    print("While loop has exited")
    print(user_list)
    user_id = user_list[0]
    print("user_id = ", user_id)
    # create_user_from_username(user_id)
    # user = "shengting.cui"

    cpus_list = []
    while True:
        cpus = input("Enter cpu request (or Enter to continue): ")
        if not cpus:
            break
        print("Your input:", cpus)
        cpus_list.append(cpus)

    print("While loop has exited")
    print(cpus_list)
    cpus = cpus_list[0]
    print("cpus = ", cpus)

    mem_list = []
    while True:
        mem = input("Enter memory request in units of MB (or Enter to continue): ")
        if not mem:
            break
        print("Your input:", mem)
        mem_list.append(mem)

    print("While loop has exited")
    print(mem_list)
    mem = int(mem_list[0]) *  1000000
    print("mem = ", mem)
    return (user_id, cpus, mem);


def initialize_redis():
    """ initialize Redis client """
    from utils.clean import clean_keys

    global redis
    try:
        redis = Redis(host=os.environ.get("REDIS_HOST", "localhost"),
                      port=os.environ.get("REDIS_PORT", 6379),
                      db=0, decode_responses=True,
                      password='***REMOVED***')
    except:
        print("redis connection error")

    clean_keys(redis)

if __name__ == "__main__":
    initialize_redis()
    keynamehelper.set_prefix("request")
    (user_id, req_cpus, req_mem) = user_request_input()
    req = Request(user_id, req_cpus, req_mem)
    req.create_user_from_username()
    req.create_request_and_validate()
    req_set_key = keynamehelper.create_key_name(user_id)
    print(redis.sscan(req_set_key))
