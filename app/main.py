# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A simple app that performs the OAuth dance and makes a Latitude request."""

__author__ = 'Ka-Ping Yee <kpy@google.com>'


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

OAUTH_CALLBACK_PATH = '/oauth_callback'
ROOT = os.path.dirname(__file__)
GOOGLE_WEATHER_API_URL = "http://www.google.com/ig/api"

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


# To set up this application as an OAuth consumer:
# 1. Go to https://www.google.com/accounts/ManageDomains
# 2. Follow the instructions to register and verify your domain
# 3. The administration page for your domain should now show an "OAuth
#    Consumer Key" and "OAuth Consumer Secret".  Put these values into
#    the app's datastore by calling Config.set('oauth_consumer_key', ...)
#    and Config.set('oauth_consumer_secret', ...).

class Config(db.Model):
    value = db.StringProperty()

    @staticmethod
    def get(name):
        config = Config.get_by_key_name(name)
        return config and config.value

    @staticmethod
    def set(name, value):
        Config(key_name=name, value=value).put()


oauth_consumer = oauth.OAuthConsumer(
    Config.get('oauth_consumer_key'), Config.get('oauth_consumer_secret'))




class GoogleVerifyDomain(webapp.RequestHandler):
    def get(self):
        self.response.out.write("""google-site-verification: googlead47db9711b4789c.html""")

class Main(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            m = model.Member()
            memster = m.get(user)
            if not memster:
                logging.info ("You is not a member")
                parameters = {
                    'scope': latitude.LatitudeOAuthClient.SCOPE,
                    'domain': Config.get('oauth_consumer_key'),
                    'granularity': 'best',
                    'location': 'all',
                    'nickname': user.nickname()
                    }
                logging.info ("Redirecting")
                oauth_webapp.redirect_to_authorization_page(
                    self, latitude.LatitudeOAuthClient(oauth_consumer),
                    self.request.host_url + OAUTH_CALLBACK_PATH, parameters)

            else:
                logging.info ("You is a member")
                member1 = model.Member.get(user)
                w = WeatherClass()
		nickname = user.nickname()
		member_delete_url = "/delete_member?nickname=%s" % nickname
		passw = member1.passw
		self.vars = {'user': user, 'member': member1,
		     'passw': passw,
                     'login_url': users.create_login_url(self.request.uri),
                     'logout_url': users.create_logout_url(self.request.uri),
                     'member_delete_url' : member_delete_url
		     }


                now = datetime.datetime.utcnow()
                weather_dict = w.get_weather(member1,now)
		if (not weather_dict):
		    self.response.out.write("Sorry, no weather here")
                else:
                    condition = weather_dict['condition']
                    temp_f = weather_dict['temp_f']
                    wind_condition = weather_dict['wind_condition']
                    city = weather_dict['city']
                    state = weather_dict['state']
                    loc = weather_dict['loc']
                    zip_code = weather_dict['zip_code']

                    self.render('templates/show_location.html', location=loc, postalCode=zip_code, temp_f=temp_f, condition=condition, wind_condition=wind_condition, city=city, state=state, vars=self.vars, pretty_app_name=my_globals.PRETTY_APP_NAME, pretty_app_phone=my_globals.PRETTY_APP_PHONE)

        else:
            self.redirect(users.create_login_url(self.request.uri))

    def render(self, path, **params):
        """Renders the template at the given path with the given parameters."""
        self.response.out.write(webapp.template.render(os.path.join(ROOT, path), params))

class DeleteMember(webapp.RequestHandler):
    def get(self):
        nickname = self.request.get('nickname')
        q =  model.Member.all().filter('nickname =', nickname)
        members = q.fetch(1)
        member = members[0]
        member.delete()
        user = users.get_current_user()
#          self.redirect("/")
        self.vars = {'user': user,
                     'login_url': users.create_login_url(self.request.uri),
                     'logout_url': users.create_logout_url(self.request.uri),
                     }

        self.render('templates/delete.html', nickname=nickname, pretty_app_name=my_globals.PRETTY_APP_NAME, pretty_app_phone=my_globals.PRETTY_APP_PHONE, app_name=my_globals.APP_NAME)

    def render(self, path, **params):
        """Renders the template at the given path with the given parameters."""
        self.response.out.write(webapp.template.render(os.path.join(ROOT, path), params))


class LatitudeOAuthCallbackHandler(webapp.RequestHandler):
    """After the user gives permission, the user is redirected back here."""
    def get(self):
        access_token = oauth_webapp.handle_authorization_finished(
            self, latitude.LatitudeOAuthClient(oauth_consumer))

        # Request the user's location
        client = latitude.LatitudeOAuthClient(oauth_consumer, access_token)
        result = latitude.Latitude(client).get_current_location()
        data = simplejson.loads(result.content)['data']
        loc = db.GeoPt(data['latitude'], data['longitude'])
            # Store a new Member object, including the user's current location.
        user =  users.get_current_user()
        their_email = user.email()

        logging.info ("Dad blast user is %s" % user)
        lnd='0123456789'
        random_password= ''.join(map(lambda x,y=lnd: choice(y), range(8)))

        member = model.Member.create(user)
	nickname = user.nickname()
        member.nickname = str(nickname)
        member.latitude_key = access_token.key
        member.latitude_secret = access_token.secret
        member.location = loc
        member.passw = random_password
        member.location_time = datetime.datetime.utcnow()
        if not member.location:
            raise utils.ErrorMessage(400, '''
    Sorry, Google Latitude has no current location for you.
    ''')
        member.put()
        logging.info ("location: %s" % member.location)
        logging.info ("passw: %s" % random_password)
        self.vars = {'user': user, 'member': member,
                     'login_url': users.create_login_url(self.request.uri),
                     'logout_url': users.create_logout_url(self.request.uri),
                     }
        self.render('templates/welcome.html', location=loc, email=their_email, passw=random_password, pretty_app_name=my_globals.PRETTY_APP_NAME, pretty_app_phone=my_globals.PRETTY_APP_PHONE, vars=self.vars)

    def render(self, path, **params):
        """Renders the template at the given path with the given parameters."""
        self.response.out.write(webapp.template.render(os.path.join(ROOT, path), params))


class UpdateLocations(webapp.RequestHandler):
    def get(self):
        limit = self.request.get('limit')
        limit = int (limit)
        cursor_name = self.request.get('cursor_name')
        query = model.ZipCode.all()
# If the app stored a cursor during a previous request, use it.
        query.order('zip')
        last_cursor = memcache.get(cursor_name)
        if last_cursor:
            query.with_cursor(last_cursor)

	results = query.fetch(limit=limit)
        # Store the latest cursor for the next request.
        cursor = query.cursor()
        memcache.set(cursor_name, cursor)
        
        work_was_done = "no"
        work_was_done_counter = 0
        for rec in results:
            lat = rec.latitude
            lng = rec.longitude
            zip = rec.zip
            logging.info ("Checking zip: %s" % zip)
            if (rec.has_location == 1):
                pass
            else:
                latlng = "%s,%s" % (lat,lng)
                if (not rec.location):
                    logging.info ("lat: %s lng: %s latlng: %s zip: %s" % (lat, lng, latlng, zip))
                    work_was_done_counter += 1
                    work_was_done = "yes"
                    rec.location = db.GeoPt(latlng)
                    rec.has_location = 1
                    rec.update_location()
                    rec.put()
        self.response.out.write ("""that was easy. Work was done %s number times: %s""" % (work_was_done, work_was_done_counter))

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
        weather_dict = self.get_weather(member,now)
        if (not weather_dict):
            trop = tropo.Tropo()
            logging.info ("No weather here")
            trop.say ("Sorry, this place doesn't have any weather")
            json = trop.RenderJson()
            return json


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
                          say="Press any key when you want more weather.", 
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
                            max_distance=16000)  # Within 100 miles.

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


class MultiWeather(webapp.RequestHandler):
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

    def authenticate_member(self, id):
            trop = tropo.Tropo()
            trop.say ("Password time for %s" % id)

            choices = tropo.Choices("[8 digits]").obj

            trop.ask(choices, 
                     say="Please enter your 8 digit password.", 
                     attempts=3, bargein=True, name="passw", timeout=5, voice="dave")

            trop.on(event="continue", 
                next="/check_password?cellnumber=%s" % id,
                say="Please hold.")

            trop.on(event="error",
                    next="/tropo_error",
                    say="Ann error occurred.")

            json = trop.RenderJson()
            logging.info ("Json result: %s " % json)
            self.response.out.write(json)

    def check_member(self, id):
        logging.info ("Checking %s to see if they are a member" % id)
        try:
	    q =  model.Member.all().filter('cellnumber =', id)
            members = q.fetch(1)
            member = members[0]
            logging.info ("I found a member: %s" % member)
        except:
            logging.info ("I came up with nothing")
            member = None
        return member




class HelloTropo(webapp.RequestHandler):
    def post(self):
    	logging.info ("Hi there")
        session_json = self.request.body
	session = tropo.Session(session_json)
	session_dict = session.dict
	id = session_dict['from']['id']
	logging.info ("id: %s" % id)


class TropoCheckPassword(webapp.RequestHandler):
    def post(self):
        cellnumber = self.request.get('cellnumber')
        json = self.request.body
        result = tropo.Result(json)
        password_attempt = result.getValue()
        logging.info ("Password attempt is: %s" % password_attempt)
        try:
            q =  model.Member.all().filter('passw =', password_attempt)
            members = q.fetch(1)
            member = members[0]
        except:
            logging.info ("I came up with nothing")
            member = None

        trop = tropo.Tropo()

        if (member):
            member.cellnumber = cellnumber
            member.put()
            trop.say ("Congratulations. Password entry accepted. From now on, when you call this number, you'll get the weather report of your current Google latitude location.")
        else:
            trop.say ("Sorry. That password was not correct.")
            choices = tropo.Choices("[1 digits]").obj
            trop.ask(choices, 
                      say="Press any key to try again.", 
                      attempts=3, bargein=True, name="zip", timeout=5, voice="dave")
            trop.on(event="continue", 
                     next="/tropo_multi_weather.py?id=%s" % cellnumber,
                     say="Ok, good luck.")

            # /tropo_multi_weather.py
        json = trop.RenderJson()
        logging.info ("Json result: %s " % json)
        self.response.out.write(json)





class SetMyOauth(webapp.RequestHandler):
    def get(self):
        ckey = "%s.appspot.com" % my_globals.APP_NAME
        Config.set('oauth_consumer_key', ckey)
        Config.set('oauth_consumer_secret', my_globals.MY_OAUTHCONSUMER_SECRET)
        self.response.out.write ("""oauth config set""")


if __name__ == '__main__':
    run_wsgi_app(webapp.WSGIApplication([
        ('/', Main),  
        ('/set_my_oauth', SetMyOauth),
        ('/check_password', TropoCheckPassword),
        ('/hello_tropo.py', HelloTropo),  
        ('/tropo_multi_weather.py', MultiWeather),  
        ('/tropo_multi_weather_continue.py', MultiWeatherContinue),  
        ('/set_my_oauth', SetMyOauth),
        ('/delete_member', DeleteMember),
        ('/locations_update', UpdateLocations),
        ('/googlead47db9711b4789c.html', GoogleVerifyDomain),
        (OAUTH_CALLBACK_PATH, LatitudeOAuthCallbackHandler)
    ]))
