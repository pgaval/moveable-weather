# Copyright 2010 Moveable Weather Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Datastore model definitions."""

__author__ = 'Ted Gilchrist <egilchri@gmail.com>'

from array import array
from config import *
from geo.geomodel import GeoModel
from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import search
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from math import sin, cos, sqrt, atan2, asin, floor
from string import replace
from xml.dom import minidom
from xml.etree import ElementTree
import HTMLParser
import cgi
import datetime
import geo
import latitude
import logging
import model
import my_globals
import oauth
import oauth_webapp
import os
import re
import simplejson
#import cjson as jsonlib
import string
import time
import tropo
import utils
import wsgiref.handlers

from config import *
from member import * 
import pprint

DEBUG = 0
max_reversals = 2

class WikipediaClass(webapp.RequestHandler):

    def get_wikipedia_entries (self,member,now):
        token = oauth.OAuthToken(member.latitude_key, member.latitude_secret)
        client = latitude.LatitudeOAuthClient(oauth_consumer, token)
        result = latitude.Latitude(client).get_current_location()
        data = simplejson.loads(result.content)['data']
        # self.response.out.write("data: %s" % data)
        logging.info ("Getting the tide")
        if 'latitude' in data and 'longitude' in data:
            lat = data['latitude']
            lng = data['longitude']
            lat = float(lat)
            lng = float(lng)
	    maxRows = 30
	    radius = 4
            logging.info ("Getting the wikipedia, lat: %s lng: %s" % (lat,lng))
            url = "http://ws.geonames.org/findNearbyWikipediaJSON?lat=%s&lng=%s&maxRows=%s&radius=%s" % (lat, lng, maxRows, radius)
            wikipedia_dict = self.get_local_entries(url)
	    return wikipedia_dict

    def get_local_entries(self, url):
        logging.info ("Calling get_local_entries: %s" % url)
        result_dict = {}
        try:
            logging.info ("response = urlfetch.fetch(%s)" % url)
            response = urlfetch.fetch(url)
        except:
          result_dict["error"] = "fetching"
          # DICT error: fetching
          return result_dict
        logging.info ("I am still alive")
        if response.status_code != 200:
          logging.info ("Had a big problem fetching wikipedia data")
          result_dict["error"] = "fetching"
          return result_dict
          # DICT error: fetching
        logging.info ("I remain alive")
        result_json = response.content
        logging.info ("result_json: %s " % result_json)
	result_data = simplejson.loads(result_json)
#	result_data = jsonlib.loads(result_json)
        logging.info ("result_data: %s " % result_data)
	return result_data



    def tropo_report_wikipedia(self, member, continuously):
        now = datetime.datetime.utcnow()
        wikipedia_dict = {}
        try:
            wikipedia_dict = self.get_wikipedia_entries(member,now)
            
        except:
            trop = tropo.Tropo()
            logging.info ("No tide here")
            trop.say ("There was a problem retrieving the tide")
        if (not wikipedia_dict):
            trop = tropo.Tropo()
            logging.info ("No wikipedia entry here")
            trop.say ("Sorry, this place doesn't have any wikipedia entries")
        else:
            trop = tropo.Tropo()
	    geonames = wikipedia_dict['geonames']
	    for geoname in geonames:
	    	trop.say("""Location: %s""" % geoname['title'])

        if (continuously):
            cellnumber = member.cellnumber
            choices = tropo.Choices("[1 digits]").obj

            trop.ask(choices, 
                     say="Press any key when you want to hear the updated Wikipedia Info.", 
                     attempts=3, bargein=True, name="zip", timeout=5, voice="dave")
            
            trop.on(event="continue", 
                         next="/tropo_multi_wikipedia_continue.py?id=%s" % cellnumber,
                         say="Please hold.")
        json = trop.RenderJson()
        logging.info ("tropo_report_tide json: %s" % json)
        return json



    def render(self, path, **params):
        """Renders the template at the given path with the given parameters."""
        self.response.out.write(webapp.template.render(os.path.join(ROOT, path), params))


    def initialize(self, request, response):
        """Sets up useful handler variables for every request."""
        webapp.RequestHandler.initialize(self, request, response)
        self.user = users.get_current_user()
        self.member = model.Member.get(users.get_current_user())
#        if self.user:
#            self.xsrf_key = Config.get_or_generate('xsrf_key')

        # Populate self.vars with useful variables for templates.
        agent = request.headers['User-Agent']
        is_mobile = re.search('iPhone|Android', agent) or request.get('mobile')
        self.vars = {'user': self.user, 'member': self.member,
                     'login_url': users.create_login_url(request.uri),
                     'logout_url': users.create_logout_url(request.uri),
                     'is_mobile': is_mobile}


class MultiWikipediaContinue(webapp.RequestHandler):
    def post(self):
        id = self.request.get('id')
        mw = MultiWikipedia()
	member = mw.check_member(id)
        if (member):
            w = WikipediaClass()
            wjson = w.tropo_report_wikipedia(member, 1)
            self.response.out.write(wjson)
        else:
            mw = MultiWikipedia()
            mw.authenticate_member(id)


class MultiWikipedia(Membership):
    def post(self):
        id = self.request.get('id')
	logging.info ("Mutitide ok, that id is: %s" % id)
	logging.info ("I am here. Ya got that?")
	if (not id):
	    session_json = self.request.body
	    session = tropo.Session(session_json)
	    session_dict = session.dict
	    id = session_dict['from']['id']
	logging.info ("id: %s" % id)
	member = self.check_member(id)

        if (member):
            w = WikipediaClass()
            wjson = w.tropo_report_wikipedia(member, 1)
            self.response.out.write(wjson)
        else:
            self.authenticate_member(id)

    def get(self):
        id = self.request.get('cellnumber')
	member = self.check_member(id)
        if (member):
            w = TideClass()
            wjson = w.tropo_report_tide(member, 1)
            self.response.out.write(wjson)
        else:
            mw = MultiWikipedia()
            mw.authenticate_member(id)






