#!/usr/bin/env python3.7
import os
import time
import re
import json
import yaml
from slackclient import SlackClient
import safygiphy
import requests
from io import BytesIO
from PIL import Image
import urllib3
urllib3.disable_warnings()

# Supported Envs
dont = ""
EnvsCanView=['dev', 'pre-prod-1', 'pre-prod-2', 'pre-prod-3', 'prod']


GiphyApiKey="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

dirpath = os.getcwd()
print("current directory is : " + dirpath)
foldername = os.path.basename(dirpath)
print("Directory name is : " + foldername)

# Tokens
slack_oauth_token = "xoxp-xxxxxxxxxxx-xxxxxxxxxxx-xxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxx"
slack_bot_token = "xoxb-xxxxxxxxxxx-xxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxx"



slack_client = SlackClient(slack_bot_token)

starterbot_id = None

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
COMD_LIST = ["giphy something","wttr city","pp3 status"]
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"

def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    #print("slack_events : " + str(slack_events))
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            user_id, message = parse_direct_mention(event["text"])
            if user_id == starterbot_id:
                return message, event["channel"]
    return None, None

def parse_direct_mention(message_text):
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def post_image_to_channel(self, channel_name, filepath, cityy):
    tile = "Weather " + cityy
    ret = slack_client.api_call(
           'files.upload',
            channels=channel_name,
            file=open(filepath, 'rb'),
            content=filepath,
            filename=filepath,
            title=tile,
            username='BotUser',               
            )
    #return ret

def get_giphy(subject):
    g = safygiphy.Giphy()
    r = g.random(tag=subject)
    if not r: return None
    return r['data']['images']['downsized']['url']

def get_wttr(city):
    url="http://wttr.in/"+str(city)+".png"
    #url="http://wttr.in/"+str(city)+"?0"
    r = requests.get(url)
    cityy = city
    #print (r)
    open(str(city), 'wb').write(r.content)
    post_image_to_channel(channel, channel, dirpath+"/"+str(city),cityy)
    donothing = "donot"
    return donothing
    #return "Weather for " + str(city)
    #print(r.encoding)
    #r.encoding = 'ISO-8859-1'
    #return "```"+str(r.text)+"```"


def current_version(env):
    env_new=env.split(" ")[0]
    prd=env.split(" ")[1]
    print("env_new : " + env_new)
    print("prd : " + prd)
    if not env_new in EnvsCanView:
        return 'Environment %s not found or not supported' % (env_new)
    url = 'https://pre-prod-1.local.com/env/raw/master/dc/%s.yaml' % (env_new)
    r = requests.get(url, verify=False)

    web_file_name = dirpath + "/pp3-2.yaml"
    f=open(web_file_name, 'w+')
    f.write(r.text)
    f.close

    with open(web_file_name, 'r') as f:
        doc = yaml.load(f)
    
    print("prd here: " + prd)
    txt = doc[prd]["ref"]
    print(txt)
    return "Product `" + prd + "` Version in `" + env_new + "` : `" + txt + "`"

def get_pp3_status(x):
    env =  re.match('status (.*)', command).groups()[0]
    #prd =  re.match('status (.*)', command).groups()[1]
    #print("env : " + env)
    #print("env : " + prd)
    resp = current_version(env)
    return resp


def handle_command(command, channel):
    default_response = ""
    MESSAGE = "```Not sure what you mean. Try @BotUser "

    for x in COMD_LIST:
        default_response = MESSAGE + x + "```" + "\n" + default_response

    response = None
    if command.startswith("giphy"):
        x = re.match('giphy (.*)', command).groups()[0]
        response = get_giphy(x)
    elif command.startswith("wttr"):
        x = re.match('wttr (.*)', command).groups()[0]
        response = get_wttr(x)
    elif command.startswith("status"):
        x = re.match('status (.*)', command).groups()[0]
        response = get_pp3_status(x)

    # Sends the response back to the channel
    if not "donot" in response:
        slack_client.api_call(
            "chat.postMessage",
            channel=channel,
            text=response or default_response
        )

if __name__ == "__main__":
    if slack_client.rtm_connect(with_team_state=False):
        print("StarterBot connected and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        starterbot_id = slack_client.api_call("auth.test")["user_id"]
        print("starterbot_id : " + starterbot_id)
        while True:
            command, channel = parse_bot_commands(slack_client.rtm_read())
            print("command : " + str(command) )
            print("channel : " + str(channel)) 
            if command:
                handle_command(command, channel)
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")
