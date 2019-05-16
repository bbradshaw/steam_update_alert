#!python
CHECK_DELAY_SEC = 120
BOTO_REGION = "us-east-1"
import gevent.monkey
gevent.monkey.patch_socket()
gevent.monkey.patch_ssl()  #steam client uses gevent, throws a warning if boto3 imported before steam client instantiated
from steam import SteamClient

import datetime, time
import boto3
import os
import argparse

def last_build(game_id):
    """Retrieves the timestamp of the last update to the public branch in steam"""
    sc = SteamClient()
    sc.anonymous_login()
    info = sc.get_product_info(apps=[game_id])
    fact = info['apps'][game_id]['depots']['branches']
    last_updated = int(fact['public']['timeupdated'])
    last_dt = datetime.datetime.fromtimestamp(last_updated)
    return last_dt

def check_loop(game_id, phone_number, keys):
    last_check = 0
    current_build = last_build(game_id)
    print(f"The current build is {current_build.ctime()}. Watching for changes.")
    last_check = time.time()
    access_key, secret_key = keys['AWS_ACCESS_KEY'], keys['AWS_SECRET_KEY'] 
    while True:
        now = time.time()
        time_left = last_check - now + CHECK_DELAY_SEC
        time_left = max((0, time_left))
        if time_left == 0:
            last_check = now
            if last_build(game_id) > current_build:
                send_text_message(access_key, secret_key, phone_number, "Game updated on steam.")
                print("Game updated on steam.")
                break
        else:
            time.sleep(time_left)

def send_text_message(access_key, secret_key, number, txt):
    """Use AWS SNS to send a text message"""
    sns = boto3.client("sns", aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=BOTO_REGION)
    sns.publish(PhoneNumber=f"+{number}", Message=txt)

if __name__ == "__main__":
    arg_parse = argparse.ArgumentParser(description="Send a text message when a given steam product updates", 
        epilog="requires environmental variables AWS_ACCESS_KEY and AWS_SECRET_KEY to send SMS via AWS SNS")
    arg_parse.add_argument("game_id", type=int, help="Steam game id")
    arg_parse.add_argument("phone_number", help="phone number to text")
    args = arg_parse.parse_args()
    keys = {}
    try:
        keys['AWS_ACCESS_KEY'], keys['AWS_SECRET_KEY'] = os.environ["AWS_ACCESS_KEY"], os.environ["AWS_SECRET_KEY"]
    except KeyError:
        raise OSError("Missing environment variables AWS_ACCESS_KEY and/or AWS_SECRET_KEY")
    check_loop(args.game_id, args.phone_number, keys)