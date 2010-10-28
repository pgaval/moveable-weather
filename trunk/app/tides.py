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

class TideClass(webapp.RequestHandler):

    def get_tide (self,member,now):
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
            logging.info ("Getting the tide, lat: %s lng: %s" % (lat,lng))
            port_record = self.lookup_coords(lat, lng)
            if (port_record):
                port = port_record.port
                place = port_record.place
                logging.info ("Winning port is %s" % port)
                tide_url = "http://tidesonline.nos.noaa.gov/data_read.shtml?station_info=%s" % (port)
                logging.info ("Fetching: %s" % tide_url)

                tide_dict = self.get_port_tide (tide_url, port_record)
                logging.info ("tide_dict: %s" % tide_dict)
                return tide_dict
            else:
                logging.info ("No port record was found")

    def get_port_tide(self, tide_url, port_record):
        logging.info ("Calling get_port_tide: %s" % tide_url)
    	port = port_record.port
        place = port_record.place
        tide_dict = {}
#        tide_dict["port"] = port
        tide_dict["place"] = place
        logging.info ("Calling get_port_tide at: %s %s" % (port, place))
        try:
            logging.info ("response = urlfetch.fetch(%s)" % tide_url)
            response = urlfetch.fetch(tide_url)
        except:
          tide_dict["error"] = "fetching"
          # DICT error: fetching
          return tide_dict
        logging.info ("I am still alive")
        if response.status_code != 200:
          logging.info ("Had a big problem fetching tide data")
          ## self.response.out.write( "Oops. Had a problem fetching the tide data")
          tide_dict["error"] = "fetching"
          return tide_dict
          # DICT error: fetching

        content = response.content
        logging.info ("tide content: %s " % content)

           #choose_port is the number of the port

        calltime = datetime.datetime.now()
      #     logging.info ("Logging a call %s %s %s " % (calltime, nearest_port, cellnumber))
        logging.info ("Port: %s place: %s" % (port, place))
        logging.info ( "Retrieving the tide information from tide station at %s at longitude %.4f .  " % (place, port_record.longitude))
        base_lng = floor (port_record.longitude)
      # determine the number of zones away from Greenwich
      # Negative number is West. Postive number is East
        dst_adjust = 1
        td = base_lng / 15 + dst_adjust
        td = floor (td)
        logging.info ("Timezone delta: %d" % (td))
        tzoffset = datetime.timedelta(hours=td)
   # This must be GMT
        nowtime = datetime.datetime.now()
        logging.info ("nowtime: %s" % (nowtime))
   # This is the "local" time. We determine this by knowing the longitude
   # of the zip code that the user entered, or that of the zip code they had
   # previously entered, and left as the default
        local_nowtime = nowtime + tzoffset
        today = local_nowtime
        logging.info ("local_nowtime: %s" % (local_nowtime))
        nhour = local_nowtime.hour
        nminute = local_nowtime.minute
        nsecond = local_nowtime.second
        logging.info ("local_nowtime hour: %d" % (nhour))
        logging.info ("local_nowtime minute: %d" % (nminute))
        local_nowtime = time.mktime(local_nowtime.timetuple())

        one_day = datetime.timedelta(days=1)
        yesterday = today - one_day
        tomorrow = today + one_day

        today = today.strftime('%m/%d/%Y')
        yesterday = yesterday.strftime('%m/%d/%Y')
        tomorrow = tomorrow.strftime('%m/%d/%Y')
        if (DEBUG == 1):
          today_message = "Today: %s" % today
          logging.info (today_message)
          yesterday_message = "Yesterday: %s" % yesterday
          logging.info (yesterday_message)
          tomorrow_message = "Tomorrow: %s" % tomorrow
          logging.info (tomorrow_message)


   # Lines in a table
        lines = content.splitlines()
   # The point of counter is to count lines in the table
   # The line corresponding to the current time has counter = 1
   # The next line has counter = 2 This is important because it enables
   # us to determine whether the tide is rising or falling
        counter = 0
 # Let's count reversals
        reversals = 0
        not_found_yet = 1
        heights = []
        for line in lines:
            if ((line.find (today) > -1) or 
                (line.find (yesterday) > -1) or
                (line.find (tomorrow) > -1)):
 # It's a line we are interested in, ie yesterday, today, or tomorrow
              if (DEBUG == 1):
                logging.info ("Line: %s" % line)
              fields = line.split()
              date = fields[0]
              thetime = fields[1]
              tz = fields[2]
              height = fields[3]
 #	      print "Date: ", date
 #	      print "Time: ", thetime
 #	      print "Tz: ", tz
 #	      print "Height: ", height

 #              heights = heights + [height]
              height = float (height)
              [month, mday, year] = date.split ("/")
              [hour, minute, second] = thetime.split (":")


              month = int (month)
              mday  = int (mday)
              year  = int (year)
              hour = int (hour)
              minute = int (minute)
              second = int (second)

 # timestamp for this current line
              linetime = time.mktime ([year, month, mday, hour, minute, second,0,0,0])
 #             print "local_nowtime: ", local_nowtime
 #	      print "linetime: ", linetime
              if ((linetime >= local_nowtime) and (not_found_yet == 1)):
 # we're at a line just a tad later than right now
                    # bingo we found it
                    logging.info ("Current tide Line: %s" % line)
                    this_height = height
                    counter = 1
                    heights = heights + [height]
                    not_found_yet = 0
                    ## self.response.out.write( "Now, at %s the height of the water is %.2f feet" % (english_time, height))
                    tide_dict["current_time"] = thetime
                    tide_dict["current_height"] = height
                    # DICT current_time: thetime
                    # DICT current_height: height
                    logging.info ("Still alive 1")
 # Get this working
              if (counter > 0):
                 logging.info ("Still alive 2")
                 heights = heights + [height]
 #		print "heights[counter-1]: ", heights[counter-1]
 # We've already found our start time, but we're searching forward
 # in the tide table for the next high or low tide


                 if (counter == 2):
 # We've got one value, and the next one will 
 # determine if rising or falling
 #  	          print "heights[2]:", heights[2]
 #  	          print "heights[1]:", heights[1]
                   logging.info ("Still alive 3")
                   if (heights[2] > heights[1]):
                     direction = "rising";
                     ## self.response.out.write ("Tide is rising.")
                     tide_dict["direction"] = "rising"
                     # DICT direction: rising
                   else:
                     direction = "falling";
                     ## self.response.out.write ("Tide is falling.")
                     tide_dict["direction"] = "falling"
                     # DICT direction: falling

                 if ((counter >= 2) and 
                     (direction == "rising") and
                      (heights[counter] < heights[counter - 1])):
 # We've detected an inflection point
                    logging.info ("Still alive 4") 
                    reversals += 1;
                    direction = "falling";
                    diff = self.humanize_time (linetime - local_nowtime)
                    logging.info ( "High tide of %.2f feet will be at %d hours %d minutes" % (height, hour, minute))

                    if (reversals == 1):
 #                     self.response.out.write( "High tide of %.2f feet will be in %s at %d hours %d minutes " % (height, diff, hour, minute))
                      ## self.response.out.write( "High tide of %.2f feet will be  at %s " % (height, english_time))
                      tide_dict["next_tide_type"] = "high"
                      tide_dict["next_tide_height"] = height
                      tide_dict["next_tide_time"] = thetime

                    # DICT next_tide_type: high
                    # DICT next_tide_height: height
                    # DICT next_tide_time: thetime

                    else:
 #                     self.response.out.write( "After that, high  tide of %.2f feet will be in %s at %d hours %d minutes" % (height, diff, hour, minute))
                      ## self.response.out.write( "After that, high  tide of %.2f feet will be at %s" % (height, english_time))
                      tide_dict["next_tide_type2"] = "high"
                      tide_dict["next_tide_height2"] = height
                      tide_dict["next_tide_time2"] = thetime

                    # DICT next_tide_type2: high
                    # DICT next_tide_height2: height
                    # DICT next_tide_time2: thetime

                    if (reversals >= max_reversals):
                      tide_dict["error"] = ""
                      return tide_dict
 # We've detected an inflection point
                 elif ((counter >= 2) and 
                       (direction == "falling") and
                       (heights[counter] > heights[counter - 1])):
                    reversals += 1;
                    direction = "rising";
                    diff = self.humanize_time (linetime - local_nowtime)
                    logging.info ( "Low tide of %.2f feet will be at %d hours %d minutes" % (height, hour, minute))
                    if (reversals == 1):
 #                     self.response.out.write( "Low tide of %.2f feet will be in %s at %d hours %d minutes" % (height, diff, hour, minute))
                      ## self.response.out.write( "Low tide of %.2f feet will be at %s" % (height, english_time))
                      tide_dict["next_tide_type"] = "low"
                      tide_dict["next_tide_height"] = height
                      tide_dict["next_tide_time"] = thetime

                    # DICT next_tide_type: low
                    # DICT next_tide_height: height
                    # DICT next_tide_time: thetime

                    else:
 #                     self.response.out.write( "After that, low tide of %.2f feet will be in %s at %d hours %d minutes" % (height, diff, hour, minute))
                      ## self.response.out.write( "After that, low tide of %.2f feet will be at %s" % (height, english_time))
                      tide_dict["next_tide_type2"] = "low"
                      tide_dict["next_tide_height2"] = height
                      tide_dict["next_tide_time2"] = thetime

                    # DICT next_tide_type2: low
                    # DICT next_tide_height2: height
                    # DICT next_tide_thetime2: thetime

                    if (reversals >= max_reversals):
                      tide_dict["error"] = ""
                      return tide_dict

 # We've got our high or low tide inflection point, and now
 # we're going to figure out 
                 counter +=1;                               
 # End get this working

    def humanize_time(self, secs):
        mins, secs = divmod(secs, 60)
        hours, mins = divmod(mins, 60)
        retstring = "%d hours %d minutes" % (hours, mins)
        return retstring

    def humanize_the_time(self, thetime):
      [hour, minute, second] = thetime.split (":")
      hour = int (hour)
      minute = int (minute)
      second = int (second)

      am_pm = ""
      if (hour >= 12):
        am_pm = "pee em"
      else:
        am_pm = "ay em"
      if (hour == 0):
        english_hour = 12
      elif (hour > 12):
        english_hour = hour - 12
      else:
        english_hour = hour
      if (minute > 0):
        if (minute == 1):
          english_minute = "1 minute"
        elif (minute < 10):
          english_minute = "oh %d" % minute
        else:
          english_minute = "%d" % minute

      else:
        english_minute = "o'clock"
      english_time = "%d  %s %s" % (english_hour, english_minute, am_pm)
      return english_time


    def tropo_report_tide(self, member, continuously):
        # w = TideClass()
        now = datetime.datetime.utcnow()
        tide_dict = {}
        try:
            tide_dict = self.get_tide(member,now)
            
        except:
            trop = tropo.Tropo()
            logging.info ("No tide here")
            trop.say ("There was a problem retrieving the tide")
        if (not tide_dict):
            trop = tropo.Tropo()
            logging.info ("No tide here")
            trop.say ("Sorry, this place doesn't have any tide")
        else:
            trop = tropo.Tropo()
            current_time = tide_dict["current_time"]
            current_height = tide_dict["current_height"]
            direction = tide_dict["direction"]
            if (direction == "rising"):
                tide_polarity1 = "High"
                tide_polarity2 = "low"
            else:
                tide_polarity1 = "Low"
                tide_polarity2 = "high"

            place = tide_dict["place"]
#            place = "Los Angeles"
            next_tide_type = tide_dict["next_tide_type"]
            next_tide_height = tide_dict["next_tide_height"]
            next_tide_time = tide_dict["next_tide_time"]
            next_tide_type2 = tide_dict["next_tide_type2"]
            next_tide_height2 = tide_dict["next_tide_height2"]
            next_tide_time2 = tide_dict["next_tide_time2"]
    
            current_time = self.humanize_the_time (current_time)
            next_tide_time = self.humanize_the_time (next_tide_time)
            next_tide_time2 = self.humanize_the_time (next_tide_time2)
    
            # match place to 2 letter state abbrev
	    m = re.match('.*([A-Z]{2}).*', place)

	    if m:
                abbrev = m.group(1)
                if abbrev in my_globals.STATE_ABBREV:
                    state = my_globals.STATE_ABBREV[abbrev]
                    place = place.replace(abbrev, state)
            trop.say("""Now, from %s at %s the height of the water is %.2f feet. Tide is %s. %s tide of %.2f feet will be  at %s. After that, %s tide of %.2f feet will be at %s""" % (place, current_time, current_height, direction, tide_polarity1, next_tide_height, next_tide_time, tide_polarity2, next_tide_height2, next_tide_time2))

        if (continuously):
            cellnumber = member.cellnumber
            choices = tropo.Choices("[1 digits]").obj

            trop.ask(choices, 
                     say="Press any key when you want to hear the updated tide.", 
                     attempts=3, bargein=True, name="zip", timeout=5, voice="dave")
            
            trop.on(event="continue", 
                         next="/tropo_multi_tides_continue.py?id=%s" % cellnumber,
                         say="Please hold.")
        json = trop.RenderJson()
        logging.info ("tropo_report_tide json: %s" % json)
        return json

    def lookup_coords (self, lat, lng):
        # Loop through items in the db. Return the item
        # whose latitude and longitude most closely match latitude and longitude    
      closest_dist = 2000
      # ok, Ports rather than ZipCode, is our model
      port_records = model.Port.proximity_fetch(
                            model.Port.all(),  # Rich query!
                            geo.geotypes.Point(lat, lng),  # Or db.GeoPt
                            max_results=10,
                            max_distance=128000)  # Within 100 miles.

      closest_port_record = ""
      for port_record in port_records:
        logging.info ("At least that is one port record: %s at %s" % (port_record.port, port_record.place))
        
        if (port_record.good_data == 0):
            continue
        lat_diff = abs (abs (port_record.latitude) - abs (lat))
        lng_diff = abs (abs (port_record.longitude) - abs (lng))
        dist = self.approx_ellipsoid_dist ((lat, lng), (port_record.latitude, port_record.longitude))
        if (dist < closest_dist):
          closest_dist = dist
          closest_port_record = port_record
          logging.info ("Closest Port_Record so far port: %s place: %s" % (closest_port_record.port, closest_port_record.place))

      logging.info ("Returning Closest Port_Record so far port: %s place: %s" % (closest_port_record.port, closest_port_record.place))
      return (closest_port_record)

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

        
class PortCleaner(webapp.RequestHandler):
  def get(self):
      limit = self.request.get('limit')
      limit = int (limit)
      cursor_name = self.request.get('cursor_name')
      query = model.Port.all()
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
      for port in results:
        good_so_far = 1
        port_number = port.port
        logging.info ("Ze port number is %s" % port_number)
        if (port.cleaned == 1):
            pass
        else:
            logging.info ("Ze port is not cleaned")
            work_was_done = "yes"
            work_was_done_counter += 1
            url = "http://tidesonline.nos.noaa.gov/data_read.shtml?station_info=%s" % (port_number)
            result = urlfetch.fetch(url)
            if result.status_code == 200:
              lines = result.content.splitlines()
              counter = 0
              not_found_yet = 1
      # Sorry, no data exists for 9410689 at this time.
              no_data = "Sorry, no data exists"
              good_so_far = 1
              for line in lines:
                 if ((line.find (no_data) > -1) ):
                   good_so_far = 0
              if (good_so_far == 1):
                  port.good_data = 1
                  port.cleaned = 1
                  return_val = port.put()
                  logging.info ("return val: %s" % return_val)
              else:
                  port.good_data = 0
                  port.cleaned = 1
                  return_val = port.put()
                  logging.info ("return val: %s" % return_val)
      self.response.out.write ("""that was easy. Work was done %s , number times: %s\n""" % (work_was_done, work_was_done_counter))

  def put_new_port (self, port, truefalse):
    name = port.place
    port_number = port.port
    lat = port.latitude
    lng = port.longitude
# 1611400,"Nawiliwili, HI",21.9550, 159.3567
    logging.info ("%s,\"%s\",%.4f,%.4f,%s" % (port_number, name, lat, lng, truefalse))

    port.good_data = truefalse
    port.cleaned = 1
    port.put()
    self.response.out.write("port %s %s is %s\n" % (name, port_number, truefalse))


class MultiTideContinue(webapp.RequestHandler):
    def post(self):
        id = self.request.get('id')
        mw = MultiTide()
	member = mw.check_member(id)
        if (member):
            w = TideClass()
            wjson = w.tropo_report_tide(member, 1)
            self.response.out.write(wjson)
        else:
            mw = MultiTide()
            mw.authenticate_member(id)


class MultiTide(Membership):
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
            w = TideClass()
            wjson = w.tropo_report_tide(member, 1)
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
            mw = MultiTide()
            mw.authenticate_member(id)






