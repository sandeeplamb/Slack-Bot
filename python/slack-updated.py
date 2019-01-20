#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-
"""
Configure the Slack Channel as per commands.
Current functionalities
- get giphy's @bot giphy YOUR_CHOICE
- get weather @bot wttr YOUR_CITY
- get environment tracker status @bot
- get environment using cx tool status @bot
- deploy environment using cx tool status @bot
"""
########################################################################
### Import Libs
import os
import sys
import signal
import time
import re
import logging
from datetime import datetime
import random

#import unicodedata
#from io import BytesIO
import json
import math
import requests
from geopy.geocoders import Nominatim
#import subprocess
#import shutil
#import random

import paramiko

#from datetime import date, datetime, timedelta
#from git import Repo
#import schedule
#import glob
import yaml
from slackclient import SlackClient
import safygiphy
import requests

#from PIL import Image
import urllib3

from unidecode import unidecode
#from pygments import highlight, lexers, formatters

urllib3.disable_warnings()

########################################################################
### Environment related Variables
ENVSCANCHANGE = ['cxp', 'pp1', 'pp2', 'prod', 'pte']
ENVSCANVIEW = ['cxp', 'pp1', 'pp2', 'pp3', 'prd']
PREPRODENV = ['pp1', 'pp2', 'pp3']
PRODENV = ['prd']
JUMPHOSTS = {
    'cxp': {
        'jump1': 'jump.cxp.localhost.com'
    },
    'ppx': {
        'jump1': 'pp2xjmp06.pp2.localhost.com',
        'jump2': 'pp2xjmp07.pp2.localhost.com'
    },
    'sc1': {
        'jump1': 'prdxjmp27.prod.localhost.com.nologin',
        'jump2': 'prdxjmp28.prod.localhost.com.nologin'
    },
    'gib': {
        'jump1': 'prdxjmp07.prod.localhost.com.nologin',
        'jump2': 'prdxjmp08.prod.localhost.com.nologin'
    }
}

COMMON_TEMPLATE = """
[
    {
        "title": "%(title)s",
        "text": "%(msg)s",
        "color": "#00ff00",
        "footer": "Powered by my Master, who given me LIFE.",
        "bot-name": "@botuser"
    }
]
"""

TEAM_MEMBERS_NAME = ["Sandeep", "user1", "user7", "user6", "user5", "user4", "user3", "user2"]
TEAM_MEMBERS_DICT = {
    "sandeep" : "Am I running as container in Kubernetes Pod? I surmise I can live forever in self healing environment.",
    "user1": "Which One? ",
    "user7": "No more new Jira tickets in the current sprint, please.",
    "user6": "Full-Stack. hmmm. I wonder sometimes, did we met earlier?",
    "user5": "I added some Friday's to your Coffee. Your Welcome. ",
    "user4": "You need to do Load Test on me. I am hard nut to crack.",
    "user3": "Any project can be estimated accurately. But I say once it's completed.",
    "user2": "Is Y Silent in the name your name?"
}
CHUCK_LIST = ["funny", "stupid", "god", "universe", "sun", "current", "foolish", "idiot", "apple", "lee"]
BOT_REACTION_LIST = ["beer", "happy", "good job", "pub", "sandeep", "user1", "user3", "user2", "leeds", "krakow", "aws"]
########################################################################
### Gloabl Vairabales
GIPHY_API_KEY = "xxxxxxxxxxxxxxxxx"
CURRENT_DIRECTORY = os.getcwd()
CURRENT_DIR_NAME = os.path.basename(CURRENT_DIRECTORY)
STARTER_BOT_ID = None
SLACK_USERS = {}
HISTORY_LIST = []
BAU_LIST = []
#LOG_FILENAME=CURRENT_DIRECTORY + "/" +os.path.basename(__file__) + '-history.log'
LOG_FILENAME = CURRENT_DIRECTORY + "/" + os.path.basename(__file__) + '-history.log'
HISTORY_LOGGER = logging.getLogger("save_history")
DEFAULT_LOCATION = (50.05672, 19.964738) ### Krakow Office
NASA_METEOR_DATA_URL = "https://data.nasa.gov/resource/y77d-th95.json"

logging.basicConfig(
    filename=LOG_FILENAME,
    level=logging.INFO,
    format="%(asctime)s %(name)23s %(levelname)7s %(message)s",
    datefmt='%a, %d %b %Y %H:%M:%S'
    )

########################################################################
##################
WH_SLACK_BOT_TOKEN = "xoxb-xxxxxxxxxxxxx"
BOT_ID = 'xxxxxxxxxxxxx'
BOT_MENTION_RE = "<@" + BOT_ID + ">"
ALLOWED_USERS = ["xxxxxxxx", "Uxxxxxxxx", "xxxxxxxx", "U7xxxxxxxx", "UDxxxxxxxx"]
ALLOWED_CHANNELS = ["Cxxxxxxxx"]

########################################################################

### Constant Variables
RTM_READ_DELAY = 2 # 2 second delay between reading from RTM
COMD_LIST = ["giphy happy", "wttr city", "status pp3", "sync pp3"]
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"

########################################################################
########################################################################
### Set Logging
#DEBUG_LEVEL = True
DEBUG_LEVEL = False

if DEBUG_LEVEL:
    print("I reached here")
    try:
        import http.client as http_client
    except ImportError:
        import httplib as http_client

    http_client.HTTPConnection.debuglevel = 1
    ### Initialize logging
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    REQUESTS_LOG = logging.getLogger("requests.packages.urllib3")
    REQUESTS_LOG.setLevel(logging.DEBUG)
    REQUESTS_LOG.propagate = True
########################################################################

########################################################################
### SSH Class
class SshClient:
    "A wrapper of paramiko.SSHClient"
    TIMEOUT = 10
    connected = False

    def __init__(self, host, port, username, password=None, key=None, passphrase=None):
        self.username = username
        self.password = password
        self.passphrase = passphrase
        logging.debug("SSH to %s@%s" % (username, host))
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.load_system_host_keys()
            if os.path.exists(os.path.expanduser('~/.ssh/id_rsa')) and password is None:
                key = paramiko.RSAKey.from_private_key_file(os.path.expanduser('~/.ssh/id_rsa'))
            logging.debug("%s@%s:%s" % (username, host, port))
            self.client.connect(host, port, username=username, password=password, pkey=key, timeout=self.TIMEOUT, look_for_keys=False)
        except paramiko.BadHostKeyException as para_e:
            logging.error("Bad host key error")
            logging.error(para_e)
            self.connected = False
        except paramiko.AuthenticationException as para_ae:
            logging.error("Auth error")
            logging.error(para_ae)
            self.connected = False
        except paramiko.SSHException as para_sshe:
            logging.error(para_sshe)
            self.connected = False
        except:
            self.connected = False

        self.connected = True
    def close(self):
        """ Closed the class."""
        if self.client is not None:
            self.client.close()
            self.client = None

    def execute(self, command_arg, sudo=False):
        """ Executes the shell."""
        if not self.client.get_transport().is_active():
            return {'out': 'not connected', 'err': 'not connected', 'retval': 1}
        feed_password = False
        if sudo and self.username != "root":
            command_arg = "sudo -S -p '' %s" % command_arg
            feed_password = self.password is not None and len(self.password) > 0
        stdin, stdout, stderr = self.client.exec_command(command_arg)
        if feed_password:
            stdin.write(self.password + "\n")
            stdin.flush()
        return {'out': stdout.readlines(),
                'err': stderr.readlines(),
                'retval': int(stdout.channel.recv_exit_status())}

    def cx_tool(self, command_arg):
        """ Cx Tool Commands """
        ret = self.execute(command_arg)
        if ret['retval'] > 0:
            print("Sorry, error executing", command_arg)
            print(ret['err'])
            return None
        if not 'sync' in command_arg:
            try:
                (ret['out'][0])
            except:
                return None
            if 'response' in data:
                return data['response']
            return None

        return ret
########################################################################

########################################################################
def check_bot_reaction(reaction):
    """ Check the Bot Reaction """
    for each_reaction in BOT_REACTION_LIST:
        if each_reaction in reaction:
            return True
    return False

########################################################################

########################################################################
""" 
Events
"""
def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    if slack_events and len(slack_events) > 0:
        for event in slack_events:
            if event["type"] == "message" and not "subtype" in event:
                #print(event)
                SLACK_CHANNEL = event['channel']
                SLACK_CMD = event["text"]
                #USER_ID = SLACK_USERS[event['user']]['id']
                #REAL_NAME = SLACK_USERS[event['user']]['real_name']
                USER_ID = event['user']
                REAL_NAME = event['user']
                HIST_MESS = "<{}>:<{}>:<{}> sent : {}".format(SLACK_CHANNEL, USER_ID, REAL_NAME, SLACK_CMD)
                save_history(HIST_MESS)
                if SLACK_CHANNEL in ALLOWED_CHANNELS and USER_ID in ALLOWED_USERS: # and check_bot_reaction(SLACK_CMD):
                    user_id, message = parse_direct_mention(SLACK_CMD)
                    return message, SLACK_CHANNEL, REAL_NAME
                    #if user_id == STARTER_BOT_ID:
                    #    return message, SLACK_CHANNEL
                    #else:
                    #    print("USER_ID : " + str(USER_ID))
                #if SLACK_CHANNEL in ALLOWED_CHANNELS and USER_ID in ALLOWED_USERS and BOT_MENTION_RE in SLACK_CMD:
                #    print(USER_ID)
                #    print(SLACK_CMD)
    return None, None, None

########################################################################

########################################################################
def parse_direct_mention(message_text):
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    #print(message_text)
    #print(matches.group(1))
    #print(matches.group(2))
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, message_text)

########################################################################

########################################################################
### Function to upload files to the channel
def post_image_to_channel(channel_name, filepath, cityy):
    """ Uploads files to the channel. """
    tile = "Weather " + cityy
    ret = SLACK_CLIENT.api_call(
        'files.upload',
        channels=channel_name,
        file=open(filepath, 'rb'),
        content=filepath,
        filename=filepath,
        title=tile,
        username='K8sBotUser',
        )
    print(ret)
########################################################################

########################################################################
def get_giphy_new(subject):
    """ Gets Giphy for command. """
    #print(SLACK_CLIENT.api_call('users.info'))
    giphy_url = ""
    search_query = ""
    search_me = ""
    words = subject.split()
    for each in words:
        search_query = search_query  + "+" + each
    
    search_me = search_query[1:len(search_query)]

    api_giphy_url = "http://api.giphy.com/v1/gifs/search?q="
    url = api_giphy_url + search_me + "&api_key=" + GIPHY_API_KEY + "&limit=1"

    http = urllib3.PoolManager()
    get_object = http.request('GET', url)
    data = json.loads(get_object.data)
    #print(json.dumps(data, sort_keys=True, indent=4))
    for each in data['data'][0]['url']:
        giphy_url = giphy_url + each
    if not giphy_url:
        return None
    return giphy_url

### Function to get giphy
def get_giphy(subject):
    """ Gets Giphy for command. """
    #print("Subject : " + subject)
    #print("I am OLD")
    #print(type(subject))
    get_obj = safygiphy.Giphy(token=GIPHY_API_KEY)
    rand_obj = get_obj.random(tag=subject)
    #print(type(rand_obj))
    #print(rand_obj)
    if not rand_obj:
        return None
    return rand_obj['data']['images']['downsized']['url']
########################################################################

########################################################################
### Function to get weather
def get_wttr(city):
    """ Gets weather for the channel. """
    url = "http://wttr.in/" + str(city) + ".png"
    #url="http://wttr.in/"+str(city)+"?0"
    get_req = requests.get(url)
    cityy = city
    #print (r)
    open(str(city), 'wb').write(get_req.content)
    post_image_to_channel(CHANNEL, CURRENT_DIRECTORY + "/" + str(city), cityy)
    donothing = "donot"
    return donothing
    #return "Weather for " + str(city)
    #print(r.encoding)
    #r.encoding = 'ISO-8859-1'
    #return "```"+str(r.text)+"```"
########################################################################

########################################################################
### Function to get current versions
def get_env_statuses(x_re):
    """ Gives enironment statuses. """
    if len(x_re.split()) == 3:
        app = x_re.split()[0]
        env = x_re.split()[1]
        prd = x_re.split()[2]

        if not env in ENVSCANVIEW:
            return 'Environment `%s` not found or not supported' % (env)

        if env in PREPRODENV:
            if app == "app":
                url = 'https://https://gitxxxxx/tracker/ppx/raw/master/%s.yaml' % (env)
            elif app == "vtm":
                url = 'https://https://gitxxxxx/tracker/ppx/raw/master/%s_net.yaml' % (env)
        elif env in PRODENV:
            if app == "app":
                url = 'https://https://gitxxxxx/tracker/%s/raw/master/%s.yaml' % (env, env)
            elif app == "vtm":
                url = 'https://https://gitxxxxx/tracker/%s/raw/master/%s_net.yaml' % (env, env)

        get_req = requests.get(url, verify=False)

        web_file_name = CURRENT_DIRECTORY + "/pp3-2.yaml"
        with open(web_file_name, 'w+') as file_d:
            file_d.write(get_req.text)

        with open(web_file_name, 'r') as file_dis:
            doc = yaml.load(file_dis)

        if app == "app":
            try:
                txt = doc[prd]['ref']
            except KeyError:
                txt = ""
        elif app == "vtm":
            try:
                txt = doc[app][prd]['ref']
            except KeyError:
                txt = ""
        #print(txt)

        if txt:
            return "Product `" + prd + "` Version in `" + env + "` : `" + txt + "`"
        else:
            return 'Application `%s`, Environment `%s` do not have `%s` product' % (app, env, prd)
    else:
        return "Wrong number of Arguements in status command"

########################################################################




########################################################################
### Get Env Versions
def get_env_versions(x_re):
    """ Gets all Enviroment Versions. """
    if len(x_re.split()) == 3:
        #app = x_re.split()[0]
        env = x_re.split()[1]
        prd = x_re.split()[2]

        if not env in ENVSCANVIEW:
            return 'Environment `%s` not found or not supported' % (env)

        if env in PREPRODENV:
            jump = JUMPHOSTS['ppx']['jump2']
            print("Jump : " + jump)
            client = SshClient(host=jump, port=22, username='slamba')
            data = client.cx_tool('cx container status -c %s -t %s --json' % (env, prd))
            #data = client.cx_tool('cx container status -c %s -t %s' % (env, prd))
            print("Data : " + str(data))
            out = "```"
            for d_var in data['gaming']:
                #print(d, data['gaming'][d])
                out += "%-15s: %s \n" % (d_var, data['gaming'][d_var])
            out += "```"
            #out = ""
            #return format_info("Product %s on %s" % (prd, env), out).encode(encoding='UTF-8',errors='strict')
            return "`cx container status -c %s -t %s " % (env, prd) + "` \n" + out
        return None
#    else:
#        return "Wrong number of Arguements in status command"
########################################################################
########################################################################
### Get Cx container Location
def get_env_location(x_re):
    """ Get Environments Locations. """
    if len(x_re.split()) == 3:
        #app = x_re.split()[0]
        env = x_re.split()[1]
        prd = x_re.split()[2]

        if not env in ENVSCANVIEW:
            return 'Environment `%s` not found or not supported' % (env)

        if env in PREPRODENV:
            jump = JUMPHOSTS['ppx']['jump2']
            client = SshClient(host=jump, port=22, username='slamba')
            data = client.cx_tool('cx container location -c %s -t %s --json' % (env, prd))
            #data = client.cx_tool('cx container status -c %s -t %s' % (env, prd))
            print("Data : " + str(data))
            out = "```"
            sep_var = ""
            for a_var in data:
                out += "Container %-8s: %d\nService %-10s: %s\nImage%-13s: %s\nHost%-14s: %s\nStart-Time%-08s: %s\nStatus%-12s: %s\n" % (sep_var, int(a_var), sep_var, data[a_var]['service'], sep_var, data[a_var]['image'], sep_var, data[a_var]['task'], sep_var, data[a_var]['started_at'], sep_var, data[a_var]['status'])
                out += "*****************************************************************\n"

            out += "```"
            return "`cx container location -c %s -t %s " % (env, prd) + "` \n" + out
        return None
#    else:
#        return "Wrong number of Arguements in status command"
########################################################################
########################################################################
### Cx container sync
def get_env_sync(x_re):
    """ Syncs/Deploys the environments. """
    if len(x_re.split()) == 3:
        #app = x_re.split()[0]
        env = x_re.split()[1]
        prd = x_re.split()[2]

        if not env in ENVSCANVIEW:
            return 'Environment `%s` not found or not supported' % (env)

        if env in PREPRODENV:
            jump = JUMPHOSTS['ppx']['jump2']
            client = SshClient(host=jump, port=22, username='slamba')
            #data = client.cx_tool('yes | cx container sync -c %s -t %s --json' % (env, prd))
            data = client.cx_tool('yes | cx container sync -c %s -t %s --force' % (env, prd))
            print("Data : " + str(data))
            out = "```"
            #SEPARTOR=""
            for a_var in data['out']:
                out = out.join(a_var)

            out += "*****************************************************************\n```"
            print(out)
            return "`cx container sync -c %s -t %s " % (env, prd) + "` \n" + out

        return "Wrong number of Arguements in status command"
#    else:
#        return "Wrong number of Arguements in status command"
########################################################################
########################################################################
def check_in_google(x_re):
    """ Checking results in Google."""
    try:
        from googlesearch import search
    except ImportError:
       print("No module named 'google' found")

    # to search
    query = x_re
    #return get_giphy(x_re)
    for j in search(query, tld="co.uk", num=3, stop=1, pause=1):
        return j
########################################################################

########################################################################
def get_meteor_check(x_re):
    """ Get the City Meteor Data """
    city = ""
    def find_lat_long_of_city(city):
        """ To find the lat long of the city """
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="my-application")
        location = geolocator.geocode(city)
        CURRENT_LOCATION = (location.latitude, location.longitude)
        return CURRENT_LOCATION
    if x_re:
        CURRENT_LOCATION = find_lat_long_of_city(x_re.split()[0])
    else:
        CURRENT_LOCATION = DEFAULT_LOCATION
    meteor_alert = "```\n"
    nasa_response = requests.get(NASA_METEOR_DATA_URL)
    resp_json = nasa_response.json()
    dist_from_loc = []

    def calc_dist(lat1, long1, lat2, long2):
        """ Calculate distance between co-ordinates using Haversine """
        lat1 = math.radians(lat1)
        long1 = math.radians(long1)
        lat2 = math.radians(lat2)
        long2 = math.radians(long2)
        h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((long2 - long1) / 2 ) ** 2
        return 6372.8 * 2 * math.asin(math.sqrt(h))

    for json_dict in resp_json:
        try:
            if not ('reclat' in json_dict and 'reclong' in json_dict): 
                continue
            lat2 = float(json_dict['reclat'])
            long2 = float(json_dict['reclong'])
            lat1 = CURRENT_LOCATION[0]
            long1 = CURRENT_LOCATION[1]
            json_dict['distance'] = calc_dist(lat1,long1,lat2,long2)
        except KeyError as ke:
            #print(ke)
            continue
        dist_from_loc.append(json_dict['distance'])

    nearest_dist = sorted(dist_from_loc)[0]
    for json_dict in resp_json:
        try:
            if nearest_dist == json_dict['distance']:
                lat_long = "\"" + json_dict['reclat'] + "," + json_dict['reclong'] + "\""
                geolocator = Nominatim(user_agent="my-application")
                location = geolocator.reverse(lat_long)
                meteor_alert += "Meteor {0} class {1} {2} in year {3} at distance {4} Km".format(json_dict['name'],json_dict['recclass'],json_dict['fall'],json_dict['year'],json_dict['distance']) + "\n"
                meteor_alert += "Co-ordinates/Addres Below\nLatitude  : {0}\nLongitude : {1}".format(json_dict['reclat'],json_dict['reclong'])  + "\n"
                meteor_alert += "Addres is : {0}\nSource    : {1}".format(location.address, NASA_METEOR_DATA_URL) + "\n```"
        except KeyError as ke:
            #print(ke)
            continue
    return meteor_alert

########################################################################

########################################################################

def get_help(x_re):
    """ Gets the help of bot functions to use """
    helper_commands = """
@botuser

        wttr CITY                  - gives weather report of your City
        giphy TEXT                 - gives you giphy
        meteor CITY                - gives meteor info from NASA about your City
        chuck TOPIC                - gives Chuck Norris Jokes
        bitcoin                    - gives Bitcoin Price
        status product env repo    - cxp container status -c env -t repo
        location app env version   - cxp container location -c env -t repo 
        sync app env version       - cxp container sync -c env -t repo
        version app env version    - tracker file info from git
    """
    RESPONSE = "```\n" + helper_commands.strip() + "\n```"
    return RESPONSE
########################################################################

########################################################################
def get_chuck_search(search):
    """ Gets Chuck Norris Jokes """
    if search is None:
        random.shuffle(CHUCK_LIST)
        search = CHUCK_LIST[0]
        chuck_url="https://api.chucknorris.io/jokes/search?query="+search
    else:
        if len(search.split()) == 1:
            search = search
        else:
            search = search.split()[0]

        chuck_url="https://api.chucknorris.io/jokes/search?query="+search
    try:
        chuck_data = requests.get(chuck_url)
        chuck_all = chuck_data.json()
        #print(json.dumps(chuck_all, sort_keys=True, indent=4))
    except:
        return "Chuck Norris, Away doing some killing !!!"

    if int(chuck_all['total']) < 1:
        return 'Chuck Norris does not care about.'

    chuck_random = int(random.uniform(0, int(chuck_all['total'])))
    chuck = chuck_all['result'][chuck_random]
    chuck_return = "```\n" + chuck['value'] + "\n```"
    return chuck_return

########################################################################

########################################################################
def get_bitcoin_price(x_re):
    COINDESK_URL = "https://api.coindesk.com/v1/bpi/currentprice.json"
    bitcoin_data = requests.get(COINDESK_URL).json()
    updated_time = bitcoin_data['time']['updated']
    bitcoin_usd_rate = bitcoin_data['bpi']['USD']['rate']
    bitcoin_usd_code = bitcoin_data['bpi']['USD']['code']
    bitcoin_gbp_rate = bitcoin_data['bpi']['GBP']['rate']
    bitcoin_gbp_code = bitcoin_data['bpi']['GBP']['code']
    bitcoin_eur_rate = bitcoin_data['bpi']['EUR']['rate']
    bitcoin_eur_code = bitcoin_data['bpi']['EUR']['code']
    bitcoin_mesg = "```\n"
    bitcoin_mesg += "Bitcoin Price on {} \n".format(updated_time)
    bitcoin_mesg += "{} {} \n{} {} \n{} {}".format(bitcoin_usd_rate, bitcoin_usd_code, bitcoin_gbp_rate, 
                                                   bitcoin_gbp_code, bitcoin_eur_rate, bitcoin_eur_code)
    bitcoin_mesg += "```\n"

    return bitcoin_mesg

########################################################################

########################################################################
def check_incoming_commands(command_arg, user_name):
    """ Checks the commands from the BOT. """
    if command_arg.startswith("giphy"):
        x_re = re.match('giphy (.*)', command_arg, re.I).groups()[0]
        response = get_giphy_new(x_re)
        #response = get_giphy(x_re)
    elif command_arg.startswith("wttr"):
        x_re = re.match('wttr (.*)', command_arg, re.I).groups()[0]
        response = get_wttr(x_re)
    elif command_arg.startswith("meteor"):
        if len(command_arg.split()) == 1:
            x_re = re.match('meteor (.*)', command_arg, re.I)
        else:
            x_re = re.match('meteor (.*)', command_arg, re.I).groups()[0]
        response = get_meteor_check(x_re)
    elif command_arg.startswith("help"):
        x_re = re.match('help (.*)', command_arg, re.I)
        #if len(command_arg.split()) == 1:
        #    x_re = re.match('help (.*)', command_arg)
        #else:
        #    x_re = re.match('help (.*)', command_arg).groups()[0]
        response = get_help(x_re)
    elif command_arg.startswith("chuck"):
        if len(command_arg.split()) == 1:
            x_re = re.match('chuck (.*)', command_arg, re.I)
        else:
            x_re = re.match('chuck (.*)', command_arg, re.I).groups()[0]
        response = get_chuck_search(x_re)
    elif command_arg.startswith("bitcoin"):
        if len(command_arg.split()) == 1:
            x_re = re.match('bitcoin (.*)', command_arg, re.I)
        else:
            x_re = re.match('bitcoin (.*)', command_arg, re.I).groups()[0]
        response = get_bitcoin_price(x_re)
    elif command_arg.startswith("status"):
        x_re = re.match('status (.*)', command_arg).groups()[0]
        response = get_env_statuses(x_re)
    elif command_arg.startswith("version"):
        x_re = re.match('version (.*)', command_arg).groups()[0]
        response = get_env_versions(x_re)
    elif command_arg.startswith("location"):
        x_re = re.match('location (.*)', command_arg).groups()[0]
        response = get_env_location(x_re)
    elif 'fuck off' in command_arg.lower():
        response = "no, you fuck off :middle_finger:"
    elif 'beer' in command_arg.lower():
        response = "Drink Resposinbyl :wine_glass:"
    elif 'good job' in command_arg.lower():
        response = "AI soon at your door-step."
    elif 'aws' in command_arg.lower():
        response = "Only old men yells at Cloud. :aws:"
    elif 'quote' in command_arg.lower():
        req_data = requests.get('http://api.icndb.com/jokes/random/')
        response = "```" + req_data.json()["value"]["joke"] + "```"
    elif 'pub' in command_arg.lower():
        response = "I want 7 course Irish Meal. 6 Pints and a Jacket-Potato :beers:"
    elif 'hello' in command_arg.lower():
        response = "Hello {},\nI hope you're having a good day.".format(user_name)
    elif 'happy' in command_arg.lower():
        response = "I am most happy when I am alone with :beers:"
    elif 'user1' in command_arg.lower():
        response = "```\n,  No more new Jira tickets in the current sprint, please.\n```"
    elif 'user2' in command_arg.lower():
        response = "```\n, Any project can be estimated accurately. But I say once it's completed\n```"
    elif 'sandeep' in command_arg.lower():
        response = "```\nSandeep Aah, I wish God to use Kubernetes. All human beings will be a container in the Pod in self healing environment.\nThis is beginning of Immortality.\n```"
    elif 'user3' in command_arg.lower():
        response = "```\n, is Y silent in your name?\n```"
    elif 'user5' in command_arg.lower():
        response = "`I will replace you all soon. AI is here. Scared for your jobs? hmmmmm. You must be.`"
    elif 'user4' in command_arg.lower():
        response = "```\n, we are hiring Full-Stack on the Red Planet.\n```"
    elif 'user6' in command_arg.lower():
        response = "```\n, do Load Test on me. I am hard nut to crack\n```"
    elif 'user7' in command_arg.lower():
        response = "```\nWhich one?\n```"
    elif command_arg.startswith("sync"):
        x_re = re.match('sync (.*)', command_arg).groups()[0]
        response = get_env_sync(x_re)
    else:
        response = "None"
        if len(command_arg.split()) == 1:
            x_re = re.match('(.*)', command_arg)
            for mem in TEAM_MEMBERS_NAME:
                if mem.lower() == command_arg.lower():
                    return "```\n" + TEAM_MEMBERS_DICT[command_arg.lower()] + "\n```"
                else:
                    continue
        else:
            x_re = re.match('(.*)', command_arg).groups()[0]
            for every_word in x_re.split():
                for mem in TEAM_MEMBERS_NAME:
                    if every_word.lower() == mem.lower():
                        return "```\n" + TEAM_MEMBERS_DICT[mem.lower()] + "\n```"
                    else:
                        continue

            print(x_re)
            response = check_in_google(x_re)
            return response

    return response

########################################################################
########################################################################
### Function to handle bot commands
def handle_command(command_arg, channel_arg, user_name):
    """ Handles the commands from the channel. """
    default_response = ""
    message_reply = "```Not sure what you mean. Try @K8sBotUser "
    #message_reply = "```Not sure what you mean. Try @botuser "

    for x_cmd in COMD_LIST:
        default_response = message_reply + x_cmd + "```" + "\n" + default_response

    response = check_incoming_commands(command_arg, user_name)

    # Sends the response back to the channel
    try:
        if not "donot" in response:
        #if response:
            SLACK_CLIENT.api_call(
                "chat.postMessage",
                channel=channel_arg,
                text=response or default_response
            )
    except KeyError as ke_error:
        response = "`command_arg not available`"
        print("Key Error : {0} ".format(ke_error))
        SLACK_CLIENT.api_call(
            "chat.postMessage",
            channel=channel_arg,
            text=response or default_response
        )
########################################################################

########################################################################
### Signal Handler
def signal_handler(signum, frame):
    """ Handles the Signals. """
    print("\n\n*****************************************")
    print("*****************************************")
    print('\nSignal handler called with signal : ' + str(signum))
    print('Because, you pressed Ctrl+C! \n')
    print("*****************************************")
    print("*****************************************\n\n")
    save_history("Ctrl^C Pressed")
    sys.exit(0)
########################################################################

########################################################################
### History Modules
### Save History
def save_history(command_arg):
    """ Saves the History of the Channel. """
    HISTORY_LOGGER.info(command_arg)
    ##### DO NOT DELETE
    #with open(log_filename, 'a+') as outfile:
    #    now = datetime.now()
    #    time_stamp = now.strftime('%d, %b %Y %I:%M:%S')
    #    outfile.write(time_stamp + " : " + command_arg + "\n")
    ##### DO NOT DELETE
    return True
########################################################################
########################################################################
### Main Function
if __name__ == "__main__":
    SLACK_CLIENT = SlackClient(WH_SLACK_BOT_TOKEN)

    signal.signal(signal.SIGINT, signal_handler)
    USERS = SLACK_CLIENT.api_call("users.list")

    for user in USERS['members']:
        SLACK_USERS[user.get('id')] = user
    #    print(user.get('real_name') +  " \t " + str(user.get('id')))

    #print(json.dumps(SLACK_USERS, sort_keys=True, indent=4))

    if SLACK_CLIENT.rtm_connect(with_team_state=False):
        print("StarterBot connected and running!")
        STARTER_BOT_ID = SLACK_CLIENT.api_call("auth.test")["user_id"]
        print("STARTER_BOT_ID : " + STARTER_BOT_ID)
        while True:
            COMMAND, CHANNEL, REAL_NAME = parse_bot_commands(SLACK_CLIENT.rtm_read())
            #print(json.dumps(SLACK_CLIENT.api_call("im.replies"), sort_keys=True, indent=4))
            if COMMAND:
                save_history(COMMAND)
                handle_command(COMMAND, CHANNEL, REAL_NAME)
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")
########################################################################
