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
from weather import *
from tides import *

from random import choice
from google.appengine.api import mail
import string

from config import *

OAUTH_CALLBACK_PATH = '/oauth_callback'
GOOGLE_VERIFY_PATH = "/%s" % my_globals.GOOGLE_VERIFY_FILE
ROOT = os.path.dirname(__file__)


class GoogleVerifyDomain(webapp.RequestHandler):
    def get(self):
        self.response.out.write("""google-site-verification: %s """ % GOOGLE_VERIFY_FILE)

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
                try:
                    logging.info ("Trying to get the weather")
                    weather_dict = w.get_weather(member1,now)
                except:
                    self.response.out.write("There was a problem retrieving the weather.")
                    exit()
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
	try:
            result = latitude.Latitude(client).get_current_location()
            data = simplejson.loads(result.content)['data']
            loc = db.GeoPt(data['latitude'], data['longitude'])
        except:
            loc = db.GeoPt(40.0, -100.0)
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


class UpdatePortLocations(webapp.RequestHandler):
    def get(self):
        logging.info ("Updating my port locations")
        limit = self.request.get('limit')
        limit = int (limit)
        cursor_name = self.request.get('cursor_name')
        query = model.Port.all()
# If the app stored a cursor during a previous request, use it.
        query.order('port')
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
            port = rec.port
            logging.info ("Checking port: %s" % port)
            if (rec.has_location == 1):
                pass
            else:
                latlng = "%s,%s" % (lat,lng)
                if (not rec.location):
                    logging.info ("lat: %s lng: %s latlng: %s port: %s" % (lat, lng, latlng, port))
                    work_was_done_counter += 1
                    work_was_done = "yes"
                    rec.location = db.GeoPt(latlng)
                    rec.has_location = 1
                    rec.update_location()
                    rec.put()
        self.response.out.write ("""that was easy. Work was done %s number times: %s""" % (work_was_done, work_was_done_counter))


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
        """Check the user's 8-digit password. This password was assigned
        when they first authenticated. If we find a match in the datastore,
        we associate the incoming phone number with the member account that 
        was retrieved. """
        cellnumber = self.request.get('cellnumber')

        # This is how we get at the result was was posted to Tropo.
        json = self.request.body
        result = tropo.Result(json)
        password_attempt = result.getValue()

        try:
            q =  model.Member.all().filter('passw =', password_attempt)
            members = q.fetch(1)
            member = members[0]
        except:
            member = None

        #  #1. Create a Tropo object we will use to post back to the Tropo engine.
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
                      attempts=3, bargein=True, name="confirm", timeout=5, voice="dave")
            # Redirect back to try again.
            trop.on(event="continue", 
                     next="/tropo_multi_weather.py?id=%s" % cellnumber,
                     say="Ok, good luck.")

        # Render all the code, from #1. to here, to a json object.
        json = trop.RenderJson()
        # Post the json code back out to the Tropo engine.
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
        ('/tropo_multi_tides.py', MultiTide),  
        ('/tropo_multi_tides_continue.py', MultiTideContinue),  
        ('/set_my_oauth', SetMyOauth),
        ('/delete_member', DeleteMember),
        ('/locations_update', UpdateLocations),
        ('/port_locations_update', UpdatePortLocations),
        ('/clean_ports', PortCleaner), #cuz they don't have tide data
        (GOOGLE_VERIFY_PATH, GoogleVerifyDomain),
        (OAUTH_CALLBACK_PATH, LatitudeOAuthCallbackHandler)
    ]))
