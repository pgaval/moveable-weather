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


from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.ext.webapp.util import run_wsgi_app
import latitude
import oauth
import oauth_webapp
import model
import utils
from google.appengine.api import users
import logging
import datetime
import simplejson
import os
import re
from google.appengine.api import urlfetch
from xml.dom import minidom
from xml.etree import ElementTree
from math import sin, cos, sqrt, atan2, asin, floor
from geo.geomodel import GeoModel
import geo
import my_globals
import tropo

from random import choice
from google.appengine.api import mail
import string
from config import *
from member import * 

GOOGLE_WEATHER_API_URL = "http://www.google.com/ig/api"

ROOT = os.path.dirname(__file__)

STATE_ABBREV = {
        'AK': 'Alaska',
        'AL': 'Alabama',
        'AR': 'Arkansas',
        'AS': 'American Samoa',
        'AZ': 'Arizona',
        'CA': 'California',
        'CO': 'Colorado',
        'CT': 'Connecticut',
        'DC': 'District of Columbia',
        'DE': 'Delaware',
        'FL': 'Florida',
        'GA': 'Georgia',
        'GU': 'Guam',
        'HI': 'Hawaii',
        'IA': 'Iowa',
        'ID': 'Idaho',
        'IL': 'Illinois',
        'IN': 'Indiana',
        'KS': 'Kansas',
        'KY': 'Kentucky',
        'LA': 'Louisiana',
        'MA': 'Massachusetts',
        'MD': 'Maryland',
        'ME': 'Maine',
        'MI': 'Michigan',
        'MN': 'Minnesota',
        'MO': 'Missouri',
        'MP': 'Northern Mariana Islands',
        'MS': 'Mississippi',
        'MT': 'Montana',
        'NA': 'National',
        'NC': 'North Carolina',
        'ND': 'North Dakota',
        'NE': 'Nebraska',
        'NH': 'New Hampshire',
        'NJ': 'New Jersey',
        'NM': 'New Mexico',
        'NV': 'Nevada',
        'NY': 'New York',
        'OH': 'Ohio',
        'OK': 'Oklahoma',
        'OR': 'Oregon',
        'PA': 'Pennsylvania',
        'PR': 'Puerto Rico',
        'RI': 'Rhode Island',
        'SC': 'South Carolina',
        'SD': 'South Dakota',
        'TN': 'Tennessee',
        'TX': 'Texas',
        'UT': 'Utah',
        'VA': 'Virginia',
        'VI': 'Virgin Islands',
        'VT': 'Vermont',
        'WA': 'Washington',
        'WI': 'Wisconsin',
        'WV': 'West Virginia',
        'WY': 'Wyoming'
}

WIND_DIRECTION_DICT = {"N":"North",
                       "S":"South",
                       "E":"East",
                       "W":"West",
                       "NW": "Northwest",
                       "NE": "Northeast",
                       "SW": "Southwest",
                       "SE": "Southeast"}


class WeatherClass(webapp.RequestHandler):
    def get_weather (self,member,now):
        token = oauth.OAuthToken(member.latitude_key, member.latitude_secret)
        client = latitude.LatitudeOAuthClient(oauth_consumer, token)
        result = latitude.Latitude(client).get_current_location()
        data = simplejson.loads(result.content)['data']
        # self.response.out.write("data: %s" % data)
        if 'latitude' in data and 'longitude' in data:
            lat = data['latitude']
            lng = data['longitude']
            lat = float(lat)
            lng = float(lng)
            zip_record = self.lookup_coords(lat, lng)
            if (zip_record):
                zip_code = zip_record.zip
                city = zip_record.city
                state = zip_record.state
                logging.info ("Winning zip code is %s" % zip_code)
                google_weather_url = "%s?weather=%s&hl=en" % (GOOGLE_WEATHER_API_URL, zip_code)
                resp = urlfetch.fetch(google_weather_url)
                if (resp.status_code == 200):
                    xml = resp.content
                    logging.info ("weather xml: %s " % xml)
                    doc = ElementTree.fromstring(xml)            
                    logging.info ("doc: %s " % doc)
                    condition = doc.find("weather/current_conditions/condition").attrib['data']
                    temp_f  = doc.find("weather/current_conditions/temp_f").attrib['data']
                    wind_condition = doc.find("weather/current_conditions/wind_condition").attrib['data']
                    city1 = doc.find("weather/forecast_information/city").attrib['data']
                    logging.info ("condition: %s temp_f: %s wind_condition: %s city: %s" % (condition, temp_f, wind_condition, city))
                    loc = db.GeoPt(lat, lng)
                    member.set_location(loc, now)
                    weather_dict = {}
                    weather_dict['loc'] = loc
                    weather_dict['zip_code'] = zip_code
                    weather_dict['state'] = state
                    weather_dict['condition'] = condition
                    weather_dict['temp_f'] = temp_f
                    weather_dict['wind_condition'] = wind_condition
                    weather_dict['city'] = city
                    return weather_dict

    def tropo_report_weather(self, member, continuously):
        # w = WeatherClass()
        now = datetime.datetime.utcnow()
        weather_dict = {}
        try:
            weather_dict = self.get_weather(member,now)
            
        except:
            trop = tropo.Tropo()
            logging.info ("No weather here")
            trop.say ("There was a problem retrieving the weather")
        if (not weather_dict):
            trop = tropo.Tropo()
            logging.info ("No weather here")
            trop.say ("Sorry, this place doesn't have any weather")
        else:
            condition = weather_dict['condition']
            temp_f = weather_dict['temp_f']
            wind_condition = weather_dict['wind_condition']
            if (1):
                # NW at 6 mph
                logging.info ("wind_condition: |%s|" % wind_condition)
                p = re.compile('Wind: ([A-Z]+) at ([0-9]+) mph')
                m = p.match(wind_condition)
                direction = m.group(1)
                long_direction = WIND_DIRECTION_DICT[direction]
                wind = "%s at %s miles per hour" % (long_direction, m.group(2))
            city = weather_dict['city']
            state = weather_dict['state']
            state1 = STATE_ABBREV[state]
            loc = weather_dict['loc']
            zip_code = weather_dict['zip_code']
            trop = tropo.Tropo()
            logging.info ("%s,%s. Weather condition: %s. Temperature: %s.  %s." % (city, state1, condition, temp_f, wind))
            trop.say ("%s,%s. Weather condition: %s. Temperature: %s.  Wind: %s." % (city, state1, condition, temp_f, wind))

        if (continuously):
            cellnumber = member.cellnumber
            choices = tropo.Choices("[1 digits]").obj

            trop.ask(choices, 
                     say="Press any key when you want to hear the updated weather.", 
                     attempts=3, bargein=True, name="zip", timeout=5, voice="dave")
            
            trop.on(event="continue", 
                         next="/tropo_multi_weather_continue.py?id=%s" % cellnumber,
                         say="Please hold.")
        json = trop.RenderJson()
        logging.info ("tropo_report_weather json: %s" % json)
        return json

    def lookup_coords (self, lat, lng):
        # Loop through items in the db. Return the item
        # whose latitude and longitude most closely match latitude and longitude    
      closest_dist = 2000
      zip_records = model.ZipCode.proximity_fetch(
                            model.ZipCode.all(),  # Rich query!
                            geo.geotypes.Point(lat, lng),  # Or db.GeoPt
                            max_results=10,
                            max_distance=64000)  # Within 100 miles.

      closest_zip_record = ""
      for zip_record in zip_records:
        logging.info ("At least that is one zip record")
        lat_diff = abs (abs (zip_record.latitude) - abs (lat))
        lng_diff = abs (abs (zip_record.longitude) - abs (lng))
        dist = self.approx_ellipsoid_dist ((lat, lng), (zip_record.latitude, zip_record.longitude))
        if (dist < closest_dist):
          closest_dist = dist
          closest_zip_record = zip_record
          # logging.info ("Closest Zip_Record zip: %s city: %s" % (closest_zip_record.zip, closest_zip_record.city))

      return (closest_zip_record)

    def approx_ellipsoid_dist(self, (lat1, lon1), (lat2, lon2)):
        """approx_ellipsoid_dist((lat1, lon1), (lat2, lon2)):
        Input: lat1, lon1, lat2, lon2: latitude and longitude (in degrees) of two points on Earth.
        Output: distance in kilometers "crow fly" between the two points.
        If you want less precision use sperical_distance.
        If you want more precision use ellipsoid_distance."""
        # http://www.codeguru.com/Cpp/Cpp/algorithms/article.php/c5115/
        # By Andy McGovern, translated to Python
        DE2RA = 0.01745329252 # Degrees to radians
        ERAD = 6378.137
        FLATTENING = 1.000000 / 298.257223563 # Earth flattening (WGS84)
        EPS = 0.000000000005

        if lon1 == lon2 and lat1 == lat2:
            return 0.0
        lat1 = DE2RA * lat1
        lon1 = -DE2RA * lon1
        lat2 = DE2RA * lat2
        lon2 = -DE2RA * lon2

        F = (lat1 + lat2) / 2.0
        G = (lat1 - lat2) / 2.0
        L = (lon1 - lon2) / 2.0

        sing = sin(G)
        cosl = cos(L)
        cosf = cos(F)
        sinl = sin(L)
        sinf = sin(F)
        cosg = cos(G)

        S = sing*sing*cosl*cosl + cosf*cosf*sinl*sinl
        C = cosg*cosg*cosl*cosl + sinf*sinf*sinl*sinl
        W = atan2(sqrt(S), sqrt(C))
        R = sqrt(S*C) / W
        H1 = (3 * R - 1.0) / (2.0 * C)
        H2 = (3 * R + 1.0) / (2.0 * S)
        D = 2 * W * ERAD
        return D * (1 + FLATTENING * H1 * sinf*sinf*cosg*cosg - FLATTENING*H2*cosf*cosf*sing*sing)

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

        
class MultiWeatherContinue(webapp.RequestHandler):
    def post(self):
        id = self.request.get('id')
        mw = MultiWeather()
	member = mw.check_member(id)
        if (member):
            w = WeatherClass()
            wjson = w.tropo_report_weather(member, 1)
            self.response.out.write(wjson)
        else:
            mw = MultiWeather()
            mw.authenticate_member(id)


class MultiWeather(Membership):
    def post(self):
        id = self.request.get('id')
	logging.info ("ok, that id is: %s" % id)
	if (not id):
	    session_json = self.request.body
	    session = tropo.Session(session_json)
	    session_dict = session.dict
	    id = session_dict['from']['id']
	logging.info ("id: %s" % id)
	member = self.check_member(id)

        if (member):
            w = WeatherClass()
            wjson = w.tropo_report_weather(member, 1)
            self.response.out.write(wjson)
        else:
            self.authenticate_member(id)

    def get(self):
        id = self.request.get('cellnumber')
	member = self.check_member(id)
        if (member):
            w = WeatherClass()
            wjson = w.tropo_report_weather(member, 1)
            self.response.out.write(wjson)
        else:
            mw = MultiWeather()
            mw.authenticate_member(id)




