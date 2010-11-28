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
import my_geo_utils
from BeautifulSoup import BeautifulSoup


DEBUG = 0
max_reversals = 2

class NRHPClass(webapp.RequestHandler):
    def __init__(self,  current_latitude, current_longitude):
        # These values are created
        # when the class is instantiated.
        self.current_latitude = current_latitude
        self.current_longitude = current_longitude


    def get_nrhp_entries (self,member,now, proximity_counter=1):
        # proximity_counter is that number n, which determines which
        # of the nearby items, arranged in order of closeness will be chosen
        # for a match
        # If we come to this function with a proximity_counter > 1, that
        # means that we are being called by an already running session.
        # The algorithm is, if we are being called by the user in the exact
        # same location as the previous call, then we should pick the 
        # nth closest item, where n is the proximity counter.
        data = self.get_my_location(member)
        # self.response.out.write("data: %s" % data)
        logging.info ("Getting the historic places")
        current_latitude = self.current_latitude
        current_longitude = self.current_longitude
        if 'latitude' in data and 'longitude' in data:
            lat = data['latitude']
            lng = data['longitude']
	    logging.info ("Comparing lat: %s current_latitude: %s lng: %s current_longitude: %s" % (lat, current_latitude, lng, current_longitude))

            # This is where we check whether the user has moved, since
            # the last call
	    if ((str(lat) == str(current_latitude)) and (str(lng) == str(current_longitude))):
                logging.info ("Those puppies are the same")
                # User hasn't moved. That means we want to go out to the
                # next closest item
                proximity_counter = proximity_counter + 1
		logging.info ("Bumping up the proximity counter to %s" % proximity_counter)
            else:
                # reset the proximity counter, so we will again
                # be looking for the nearest item
                proximity_counter = 1
		logging.info ("Settng the proximity counter to back to %s" % proximity_counter)

            # Remember our lat and lng, so future calls will know whether 
            # we hav moved
	    self.current_latitude = lat
	    self.current_longitude = lng
            lat = float(lat)
            lng = float(lng)
	    maxRows = 30
	    radius = 4
            logging.info ("Getting the nrhp, lat: %s lng: %s" % (lat,lng))
            #nrhp_dict = self.get_local_entries(lat,lng)
	    # return nrhp_dict
            results = self.get_local_entries(lat,lng, 10, proximity_counter)
	    return results

    def get_my_location(self, member):
        token = oauth.OAuthToken(member.latitude_key, member.latitude_secret)
        client = latitude.LatitudeOAuthClient(oauth_consumer, token)
        result = latitude.Latitude(client).get_current_location()
        data = simplejson.loads(result.content)['data']
        return data

    def get_local_entries(self, lat,lng, how_many, proximity_counter):
        logging.info ("Calling get_local_entries: %s, %s" % (lat,lng))
	current_latitude = self.current_latitude
	current_longitude = self.current_longitude
        logging.info ("Ye I just got current_latitude: %s current_longitude: %s" % (current_latitude, current_longitude))

        result_dict = {}
	closest_dist = 2000
      # ok, Ports rather than ZipCode, is our model
        # we have to retrieve more items than just how_many, because the first
        # bunch, we'll have to discard, since we've already visited them
        nrhp_records = model.NRHP.proximity_fetch(
                            model.NRHP.all(),  # Rich query!
                            geo.geotypes.Point(lat, lng),  # Or db.GeoPt
                            max_results=how_many + proximity_counter,
                            max_distance=128000)  # Within 10 miles.

        closest_nrhp = {}
        results = [] # experiment with returning a list, for now
	smallest_distance = 10000
	utils = my_geo_utils.MyGeoUtils()
	
        record_counter = 0
	proximity_counter = int(proximity_counter)
        for nrhp_record in nrhp_records:
            record_counter = record_counter + 1
	    logging.info ("record_counter: %s proximity_counter: %s" % (record_counter, proximity_counter))
            if (record_counter < proximity_counter):
	        logging.info ("Skipping %s because %s is less than %s" % (nrhp_record.title, record_counter, proximity_counter ))
                continue
            title = nrhp_record.title
            refnum = nrhp_record.refnum
            logging.info ("At least that is one nrhp record: %s at %s" % (title, refnum))
	    this_lat = nrhp_record.latitude
	    this_lng = nrhp_record.longitude
#	    km_distance = utils.approx_ellipsoid_dist ((lat,lng), (this_lat, this_lng))
	    logging.info ("utils.calculate_distance_and_bearing(%d, %d, %d, %d)" % (lat, lng, this_lat, this_lng))

            distance_n_bearing = utils.calculate_distance_and_bearing(lat, lng, this_lat, this_lng)
	    km_distance = distance_n_bearing[0]
	    bearing = distance_n_bearing[1]
	    logging.info ("That's a m distance of %.2f bearing of %s" % (km_distance, bearing))
            this_item = {'refnum' : refnum, 'title': title, 'distance': km_distance, 'bearing': bearing}
            results.append(this_item)
        return results

    def tropo_report_nrhp(self, member, continuously, proximity_counter=1):
        # proximity_counter is a record of how far down the list of closest
        # results we have travelled
        # when they hit a key, we'll go fetch more results
        # We'll either start fresh, at position 1, or we'll keep going 
        # out in wider and wider circles from our origin.

        now = datetime.datetime.utcnow()
        nrhp_dict = {}
        results = []
        choices = tropo.Choices("[1 digits]").obj	
        try:
            results =  self.get_nrhp_entries(member,now, proximity_counter)
            current_latitude = self.current_latitude
            current_longitude = self.current_longitude
            logging.info ("Ay I just got current_latitude: %s current_longitude: %s" % (current_latitude, current_longitude))


            #nrhp_dict = self.get_nrhp_entries(member,now)
            
        except:
            trop = tropo.Tropo()
            logging.info ("No historic places here")
            trop.say ("There was a problem retrieving the historic places")
#        if (not nrhp_dict):
        if (not results):
            trop = tropo.Tropo()
            logging.info ("No nrhp entry here")
            trop.say ("Sorry, this place doesn't have any nrhp entries")
        else:
            trop = tropo.Tropo()

            for nrhp_dict in results:
	    	proximity_counter = proximity_counter + 1
                title = nrhp_dict['title']
                refnum = nrhp_dict['refnum']
                distance = nrhp_dict['distance']
                bearing = nrhp_dict['bearing']
		search_url = "%s%s" % (my_globals.wikipedia_search_root, refnum)
		sayable_content = self.get_sayable_content(search_url, refnum)
                if (sayable_content):
                    sayable_bearing =  self.get_sayable_bearing (bearing)
                    sayable_distance = self.get_sayable_distance (distance)
                    statement = """%s is %s away to the %s. %s""" % (title, sayable_distance, sayable_bearing, sayable_content)
                    
                    trop.ask(choices, 
                     say=statement, 
                     attempts=3, bargein=True, name="zip", timeout=5, voice="dave")
                    cellnumber = member.cellnumber
		    # let's pass the lat and lng, and the results
		    # counter. This should help us implement a ui
		    # where, if the person doesn't move, we bump out to the 
		    # next further out result
                    trop.on(event="continue", 
                         next="/tropo_multi_nrhp_continue.py?id=%s&lat=%s&lng=%s&proximity_counter=%s" % (cellnumber, current_latitude, current_longitude, proximity_counter))
                    break
        json = trop.RenderJson()
        logging.info ("tropo_report_historic places json: %s" % json)
        return json


    def get_sayable_content (self, search_url, refnum):
        """ 
<ul class='mw-search-results'> 
<li><a href="/wiki/Rundlet-May_House" title="Rundlet-May House">Rundlet-May House</a>   <div class='searchresult'>built  | architect  | architecture  | added June 7, 1976  | visitation_num  | visitation_year  | <span class='searchmatch'>refnum</span> <span class='searchmatch'>76000133</span>  | mpsub  | governing_body <b>...</b> </div> 
<div class='mw-search-result-data'>2 KB (262 words) - 01:38, 19 October 2010</div></li> 
</ul>

"""
        logging.info ("search_url: %s" % search_url)
        resp = urlfetch.fetch(search_url)
        if (resp.status_code == 200):
            contents = resp.content
            soup = BeautifulSoup(contents)
#soup.find("b", { "class" : "lime" })
            results = soup.find("ul", {"class" : "mw-search-results"})
#            results = soup.find('p', align="center")
            result_content = ""
            if results:
                h = results.find('a')
                if (h):
                    href = h['href']
                    new_search_url = "http://en.wikipedia.org%s" % href
                    logging.info ("new_search_url: %s " % new_search_url)
                    resp = urlfetch.fetch(new_search_url)
                    if (resp.status_code == 200):
                        soup = BeautifulSoup(resp.content)
                        first_paras = soup.findAll('p')
                        final_result = ""
                        for first_para in first_paras:
                            for item in first_para.findAll(text=True):
                                final_result = "%s %s" % (final_result, item)
                        return final_result
        return ""
        


    def get_sayable_distance (self, distance):

        miles = (distance/1000) * .62                          
        num_miles = "%.0f" % miles
        num_miles = int (num_miles)
        fraction = miles - num_miles
        if (num_miles == 1):
            mile_sing_plur = "mile"
        else:
            mile_sing_plur = "miles"
        
        if ((fraction < .15) and (num_miles < 1)):
            feet = miles * 5280
            feet = "%.0f" % feet
            return "about %s feet" % feet
        else:
            if (fraction < .15):
                fraction_part = ''

            if (fraction > .15):
                fraction_part = "a quarter"

            if (fraction > .35):
                fraction_part = "a half"

            if (fraction > .65):
                fraction_part = "three quarters"

            if (fraction > .90):
                fraction_part = ""
                num_miles = num_miles + 1

            if (num_miles):
                if (fraction_part):
                    say_miles = "%s and %s %s" % (num_miles, fraction_part, mile_sing_plur)
                else:
                    say_miles = "%s %s" % (num_miles, mile_sing_plur)
            else:
                if (fraction_part == "a half"):
                    say_miles = "a half a mile"
                elif  (fraction_part == "a quarter"):
                    say_miles = "a quarter of a mile"
                elif  (fraction_part == "three quarters"):
                    say_miles = "three quarters of a mile"
            say_miles = "about %s" % say_miles
        return say_miles

    def get_sayable_bearing (self, bearing):

        
        logging.info ("We are working with a bearing of %s" % bearing)

	bearing = "%.0f" % bearing
        bearing = int(bearing)
        bearing = bearing % 360
	result_bearing = str(bearing)

	orig_bearing = result_bearing

        if (bearing >= 0):
            result_bearing = "North"
 	 
        if (bearing > 22):
            result_bearing = "Northeast"
 	 

        if (bearing > 64):
            result_bearing = "East"

        if (bearing > 112):
            result_bearing = "South East"

        if (bearing > 157):
            result_bearing = "South"

        if (bearing > 202):
            result_bearing = "Southwest"

        if (bearing > 247):
            result_bearing = "West"
	    
        if (bearing > 292):
            result_bearing = "Northwest"

        if (bearing > 337):
            result_bearing = "North"

        # debugging
        # result_bearing = "%s at %s degrees" % (result_bearing, orig_bearing)
        return result_bearing


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


class MultiNRHPContinue(webapp.RequestHandler):
    def post(self):
        id = self.request.get('id')
	proximity_counter = self.request.get('proximity_counter')
        proximity_counter = int (proximity_counter)
	current_latitude = self.request.get('lat')
	current_longitude = self.request.get('lng')
        logging.info ("Yo I just got current_latitude: %s current_longitude: %s proximity_counter: %s" % (current_latitude, current_longitude, proximity_counter))

        mw = MultiNRHP()
	member = mw.check_member(id)
        if (member):
            w = NRHPClass(current_latitude, current_longitude)
            wjson = w.tropo_report_nrhp(member, 1, proximity_counter)
            self.response.out.write(wjson)
        else:
            mw = MultiNRHP()
            mw.authenticate_member(id)


class MultiNRHP(Membership):
    def post(self):
        id = self.request.get('id')
	logging.info ("Mutihistoric places ok, that id is: %s" % id)
	logging.info ("I am here. Ya got that?")
	if (not id):
	    session_json = self.request.body
	    session = tropo.Session(session_json)
	    session_dict = session.dict
	    id = session_dict['from']['id']
	logging.info ("id: %s" % id)
	member = self.check_member(id)

        if (member):
            lat = ""
            lng = ""
            w = NRHPClass(lat, lng)
            wjson = w.tropo_report_nrhp(member, 1)
            self.response.out.write(wjson)
        else:
            self.authenticate_member(id)

    def get(self):
        id = self.request.get('cellnumber')
	member = self.check_member(id)
        if (member):
            w = NRHPClass()
            wjson = w.tropo_report_nrhp(member, 1)
            self.response.out.write(wjson)
        else:
            mw = MultiNRHP()
            mw.authenticate_member(id)






