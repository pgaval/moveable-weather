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
from random import choice
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


class ZipDeCoder(webapp.RequestHandler):
  def get(self):
    zip_code = self.request.get('zip_code')
    st = ShowTide()
    if (zip_code):
       try:
         coords = st.get_lat_lng (zip_code)      
       except:
         self.response.out.write( "Had a problem fetching the tide data for the zip code %s . Please try calling again." % zip_code)
         return
       logging.info ("Coords lat: %.4f lng: %.4f" % (coords[0], coords[1]))
       try:
         (choose_port, port_name, port_lng, port_lat) = st.get_port_from_coords (coords)          
       except:
         self.response.out.write( "Had a problem calculating the closest tide station")
       self.response.out.write( """<?xml version="1.0" encoding="UTF-8" ?> 
<points>
<point lat1="%.4f" lng1="%.4f" lat2="%.4f" lng2="%.4f" name="%s" number="%s"></point>
</points>
""" % (coords[1], coords[0], port_lat, port_lng,port_name, choose_port))


class ShowTides(webapp.RequestHandler):

  def admin_note(self, subject, body):
    user_address = '6039570051@messaging.sprintpcs.com'
    sender_address = 'egilchri@gmail.com'
    mail.send_mail(sender_address, user_address, subject, body)

  def get_tides(self):
     #choose_port is the number of the port
     resultdict = {}
     choose_port = self.request.get('choose_port')
     zip_code = self.request.get('zip_code')
     cellnumber = self.request.get('cellnumber')
     port_name = ""
     port_lat = 0
     if (cellnumber == ""):
       cellnumber = "6039570051"
     if (choose_port):
       q1 = Port.all()
       q1.filter("number =", choose_port)
       for port in q1:
         port_name = port.name
         resultdict["name"] = port_name
         port_lng = port.lng

     if (zip_code):
       try:
         coords = self.get_lat_lng (zip_code)      
       except:
         self.response.out.write( "Had a problem fetching the tide data for the zip code %s . Please try calling again." % zip_code)
         return

       try:
         (choose_port, port_name, port_lng, port_lat) = self.get_port_from_coords (coords)          
       except:
         self.response.out.write( "Had a problem calculating the closest tide station")
         return

         
# This is a new port preference (since they gave us a zip)
# so, record the preference
     user = User(cellnumber = cellnumber,
                      nearest_port = choose_port)

     # First get rid of any records having this cellnumber
     q = User.all()
     q.filter("cellnumber =", cellnumber)

     already_had_user = 0
     for user1 in q:
       already_had_user = 1
       logging.info ("First deleting %s nearest port %s " % (user1.cellnumber, user1.nearest_port))
       user1.delete();
     user.put()
     subject = "New User" 
     body = "cellnumber: %s nearest_port: %s" % (cellnumber, choose_port)
     if (already_had_user == 0):
       self.admin_note(subject, body);

# We log every call
     calltime = datetime.datetime.now()
     call = Call(cellnumber = cellnumber,
                 nearest_port = choose_port,
                 calltime = calltime,
                 )
     call.put()
#     logging.info ("Logging a call %s %s %s " % (calltime, nearest_port, cellnumber))
     logging.info ("Port number: %s Port name: %s" % (choose_port, port_name))
     logging.info ( "Retrieving the tide information from tide station at %s at longitude %.4f .  " % (port_name, port_lng))

     
#     if (choose_port == ""):
#       choose_port = "8413320"
#       cellnumber = "6039570051"
#     today = time.strftime( "%m/%d/%Y" )
     base_lng = floor (port_lng)
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

#     print "local_nowtime: ", local_nowtime
#     print "local_nowtime hour: ", nhour
# old way is next 2 lines
#     today = datetime.date.today()
#     today = today + tzoffset
     
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


# Now, go grab the tide table corresponding to this zip code
     url = "http://tidesonline.nos.noaa.gov/data_read.shtml?station_info=%s" % (choose_port)
     logging.info ("Fetching: %s" % url)
     logging.info ("Port number: %s" % choose_port)
     try:
       result = urlfetch.fetch(url)
     except:
       ## self.response.out.write( "Oops. Had a problem fetching the tide data")
       resultdict["error"] = "fetching"
       # DICT error: fetching
       return resultdict
     if result.status_code != 200:
       logging.info ("Had a big problem fetching tide data")
       ## self.response.out.write( "Oops. Had a problem fetching the tide data")
       resultdict["error"] = "fetching"
       return resultdict
       # DICT error: fetching
     elif result.status_code == 200:
# Lines in a table
        lines = result.content.splitlines()
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
                   resultdict["current_time"] = thetime
                   resultdict["current_height"] = height
		   # DICT current_time: thetime
		   # DICT current_height: height

# Get this working
             if (counter > 0):
                heights = heights + [height]
#		print "heights[counter-1]: ", heights[counter-1]
# We've already found our start time, but we're searching forward
# in the tide table for the next high or low tide

                
                if (counter == 2):
# We've got one value, and the next one will 
# determine if rising or falling
#  	          print "heights[2]:", heights[2]
#  	          print "heights[1]:", heights[1]
                  if (heights[2] > heights[1]):
                    direction = "rising";
                    ## self.response.out.write ("Tide is rising.")
                    resultdict["direction"] = "rising"
		    # DICT direction: rising
                  else:
                    direction = "falling";
                    ## self.response.out.write ("Tide is falling.")
                    resultdict["direction"] = "falling"
		    # DICT direction: falling

                if ((counter >= 2) and 
		    (direction == "rising") and
                     (heights[counter] < heights[counter - 1])):
# We've detected an inflection point
                   reversals += 1;
                   direction = "falling";
		   diff = self.humanize_time (linetime - local_nowtime)
                   logging.info ( "High tide of %.2f feet will be at %d hours %d minutes" % (height, hour, minute))

                   if (reversals == 1):
#                     self.response.out.write( "High tide of %.2f feet will be in %s at %d hours %d minutes " % (height, diff, hour, minute))
                     ## self.response.out.write( "High tide of %.2f feet will be  at %s " % (height, english_time))
                     resultdict["next_tide_type"] = "high"
                     resultdict["next_tide_height"] = height
                     resultdict["next_tide_time"] = thetime

		   # DICT next_tide_type: high
		   # DICT next_tide_height: height
		   # DICT next_tide_time: thetime

                   else:
#                     self.response.out.write( "After that, high  tide of %.2f feet will be in %s at %d hours %d minutes" % (height, diff, hour, minute))
                     ## self.response.out.write( "After that, high  tide of %.2f feet will be at %s" % (height, english_time))
                     resultdict["next_tide_type2"] = "high"
                     resultdict["next_tide_height2"] = height
                     resultdict["next_tide_time2"] = thetime

		   # DICT next_tide_type2: high
		   # DICT next_tide_height2: height
		   # DICT next_tide_time2: thetime

                   if (reversals >= max_reversals):
                     resultdict["error"] = ""
                     return resultdict
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
                     resultdict["next_tide_type"] = "low"
                     resultdict["next_tide_height"] = height
                     resultdict["next_tide_time"] = thetime

		   # DICT next_tide_type: low
		   # DICT next_tide_height: height
		   # DICT next_tide_time: thetime

                   else:
#                     self.response.out.write( "After that, low tide of %.2f feet will be in %s at %d hours %d minutes" % (height, diff, hour, minute))
                     ## self.response.out.write( "After that, low tide of %.2f feet will be at %s" % (height, english_time))
                     resultdict["next_tide_type2"] = "low"
                     resultdict["next_tide_height2"] = height
                     resultdict["next_tide_time2"] = thetime

     		   # DICT next_tide_type2: low
		   # DICT next_tide_height2: height
		   # DICT next_tide_thetime2: thetime

                   if (reversals >= max_reversals):
                     resultdict["error"] = ""
                     return resultdict

# We've got our high or low tide inflection point, and now
# we're going to figure out 
                counter +=1;                               
# End get this working

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

  def browserize_the_time(self, thetime):
    [hour, minute, second] = thetime.split (":")
    hour = int (hour)
    minute = int (minute)
    second = int (second)

    am_pm = ""
    if (hour >= 12):
      am_pm = "pm"
    else:
      am_pm = "am"
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
        english_minute = "0%d" % minute
      else:
        english_minute = "%d" % minute

    else:
      english_minute = "o'clock"
    english_time = "%d:%s %s" % (english_hour, english_minute, am_pm)
    return english_time

  def humanize_time(self, secs):
    mins, secs = divmod(secs, 60)
    hours, mins = divmod(mins, 60)
    retstring = "%d hours %d minutes" % (hours, mins)
    return retstring

  def get_lat_lng(self, my_address):
#    my_address = "Bar+Harbor,+Maine"
    key = "ABQIAAAArbyRqgj0_bOIl5_5MGyneRSss0KkgIHkkLqBbqSrQFXluxx97RTSPD_tqRvlVT8lrFqOX78M9gJKQA"
    address = "http://maps.google.com/maps/geo?q=%s&output=json&key=%s" % (my_address, key)
#    self.response.out.write("address: %s" % (address))
    result = urlfetch.fetch(address)
    if result.status_code == 200:
      json = result.content
# bail unless CountryNameCode":"US"
      logging.info ("Json is: %s" % json)
      parsed = simplejson.loads(json)
      placemark = parsed['Placemark'][0]
      point = placemark['Point']
      address = placemark['address']
      logging.info ("address: %s" % address)
      coords = point['coordinates']
#      self.response.out.write("Lat: %.4f Lng: %.4f" % (coords[0], coords[1]))
      return coords

  def get_port_from_coords (self, coords):
    my_lat = coords[1]
    my_lng = coords[0]
#    self.response.out.write("<br>%.4f, %.4f" % (my_lat, my_lng))
# Loop through ports in the db. Return the port number of the port
# whose lat and lng most closely match lat and lng    
    delta = 2
#    result = db.GqlQuery("SELECT * FROM Port WHERE lat > 20 and lng > 100")
#    for port in result:
#      nearest_port = port.number
#      nearest_port_name = port.name
#    query = db.Query(Port)
    query = Port.all()
    query.filter('int_good_data =', 1)
    closest_dist = 2000
    closest_port = ""
#    for port in query:
#      logging.info ("Candidate Port number: %s name: %s good_data %s" % (port.number, port.name, port.good_data))
    for port in query:
      lat_diff = abs (abs (port.lat) - abs (my_lat))
      lng_diff = abs (abs (port.lng) - abs (my_lng))
      dist = self.approx_ellipsoid_dist ((my_lat, my_lng), (port.lat, port.lng))
      if (dist < closest_dist):
        closest_dist = dist
        closest_port = port
        logging.info ("Closest Port number: %s name: %s good_data %s" % (closest_port.number, closest_port.name, closest_port.good_data))
#      self.response.out.write("<br>Port: %s  %.4f , %.4f Dist: %.4f" % (port.name, port.lat, port.lng, dist))
      					     	    	       	       		   
#    self.response.out.write("<br>Closest Port: %s %.4f, %.4f Dist: %.4f" % (closest_port.name, closest_port.lat, closest_port.lng, closest_dist))
#    self.response.out.write("for %s. " % (closest_port.name))
    return (closest_port.number, closest_port.name, closest_port.lng, closest_port.lat)

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


  def get(self):
    # get a parameter, that determines whether tides are spoken
    # or portrayed in a table
    mode = self.request.get('mode')

    if (mode == "browser"):
      self.response.out.write("""<html><pre>""")
      resultdict = self.get_tides()
      self.browserify_tide_result(resultdict)
      self.response.out.write("""</pre></html>""")

    elif (mode == "table"):
      self.response.out.write("""<html><body>""")
      resultdict = self.get_tides()
      self.tableify_tide_result(resultdict)
      self.response.out.write("""</body></html>""")

    else:
      self.response.out.write('<?xml version="1.0" encoding="UTF-8"?>')
      self.response.out.write("""

<!DOCTYPE vxml SYSTEM "http://www.w3.org/TR/voicexml21/vxml.dtd"> 
    <vxml version = "2.1" >
    
    <var name="from_point" expr="''" />
    <var name="to_point" expr="''" />
    <var name="useridnum" expr="" />
    <var name="firstname" expr="''" />
    <var name="where" expr= "''"/> 
    <var name="ulocate" expr= "'1'"/> 
    <var name="doing_destination" expr= ""/> 
    <!-- comment out the var and use the field "replay" when I get it working -->
    <var name="replay" expr= "0"/> 


    <form id="MyTidesForm">

    <block>
    <prompt bargein="false">



""")

      resultdict = self.get_tides()
      self.speechify_tide_result(resultdict)
      self.response.out.write("""

    </prompt>
    <return/>
    </block>

    </form>

    </vxml>
""")
  def speechify_tide_result(self, result):
    error = result["error"]
    if error == "fetching":
      self.response.out.write( "Oops. Had a problem fetching the tide data")
      return
    current_time = result["current_time"]
    current_height = result["current_height"]
    direction = result["direction"]
    if (direction == "rising"):
      tide_polarity1 = "High"
      tide_polarity2 = "low"
    else:
      tide_polarity1 = "Low"
      tide_polarity2 = "high"

    next_tide_type = result["next_tide_type"]
    next_tide_height = result["next_tide_height"]
    next_tide_time = result["next_tide_time"]
    next_tide_type2 = result["next_tide_type2"]
    next_tide_height2 = result["next_tide_height2"]
    next_tide_time2 = result["next_tide_time2"]
    
    current_time = self.humanize_the_time (current_time)
    next_tide_time = self.humanize_the_time (next_tide_time)
    next_tide_time2 = self.humanize_the_time (next_tide_time2)
    
    self.response.out.write("""Now, at %s the height of the water is %.2f feet. Tide is %s. %s tide of %.2f feet will be  at %s. After that, %s tide of %.2f feet will be at %s""" % (current_time, current_height, direction, tide_polarity1, next_tide_height, next_tide_time, tide_polarity2, next_tide_height2, next_tide_time2))

  def browserify_tide_result(self, result):
    error = result["error"]
    if error == "fetching":
      self.response.out.write( "<p>Oops. Had a problem fetching the tide data")
      return
    current_time = result["current_time"]
    current_height = result["current_height"]
    direction = result["direction"]
    if (direction == "rising"):
      tide_polarity1 = "High"
      tide_polarity2 = "low"
    else:
      tide_polarity1 = "Low"
      tide_polarity2 = "high"

    next_tide_type = result["next_tide_type"]
    next_tide_height = result["next_tide_height"]
    next_tide_time = result["next_tide_time"]
    next_tide_type2 = result["next_tide_type2"]
    next_tide_height2 = result["next_tide_height2"]
    next_tide_time2 = result["next_tide_time2"]
    
    current_time = self.browserize_the_time (current_time)
    next_tide_time = self.browserize_the_time (next_tide_time)
    next_tide_time2 = self.browserize_the_time (next_tide_time2)
    
    self.response.out.write("""<p>Now, at %s the height of the water is %.2f feet. <p>Tide is %s. <p>%s tide of %.2f feet will be  at %s. <p>After that, %s tide of %.2f feet will be at %s""" % (current_time, current_height, direction, tide_polarity1, next_tide_height, next_tide_time, tide_polarity2, next_tide_height2, next_tide_time2))


  def tableify_tide_result(self, result):
    error = result["error"]
    if error == "fetching":
      self.response.out.write( "<p>Oops. Had a problem fetching the tide data")
      return
    current_time = result["current_time"]
    current_height = result["current_height"]
    direction = result["direction"]
    if (direction == "rising"):
      tide_polarity1 = "High"
      tide_polarity2 = "low"
    else:
      tide_polarity1 = "Low"
      tide_polarity2 = "high"

    next_tide_type = result["next_tide_type"]
    next_tide_height = result["next_tide_height"]
    next_tide_time = result["next_tide_time"]
    next_tide_type2 = result["next_tide_type2"]
    next_tide_height2 = result["next_tide_height2"]
    next_tide_time2 = result["next_tide_time2"]
    name = result["name"]
    current_time = self.browserize_the_time (current_time)
    next_tide_time = self.browserize_the_time (next_tide_time)
    next_tide_time2 = self.browserize_the_time (next_tide_time2)
    
    self.response.out.write("""<h3>%s</h3>""" % (name))
    self.response.out.write("""<table border=\"1\">
<tr><th>Time</th><th>Height</th></tr>
<tr><td>%s</td><td>%.2f</td></tr>
<tr><td>%s</td><td>%.2f</td></tr>
<tr><td>%s</td><td>%.2f</td></tr>
</table>""" % (current_time, current_height, next_tide_time, next_tide_height, next_tide_time2, next_tide_height2, ))


class ChoosePort(webapp.RequestHandler):

  def get(self):
    nearest_port = 0
    cellnum = self.request.get('session.callerid')

# lookup the cellnumber in our db, If it's there, retrieve
# the nearest_port Assume this is what the user wants to use, without asking
# nearest_port = Users.get(-cellnumber = cellnum)    
    result = db.GqlQuery("SELECT * FROM User WHERE cellnumber = :1", cellnum)
    for user in result:
       nearest_port = user.nearest_port
# for testing
#    nearest_port = 0
    ask_for_zip = 1
    if (nearest_port > 0):
       choose_port = nearest_port
       ask_for_zip = 0

    self.response.out.write('<?xml version="1.0" encoding="UTF-8"?>')
    self.response.out.write("""

<!DOCTYPE vxml SYSTEM "http://www.w3.org/TR/voicexml21/vxml.dtd"> 
<vxml version = "2.1" >

<var name="new_port" expr= "0"/> 

""")
    self.response.out.write("<var name=\"ask_for_zip\" expr=\"%s\"/>" % (ask_for_zip))

    self.response.out.write("<form>")


    self.response.out.write("<var name=\"where\"/>")
    self.response.out.write("<var name=\"cellnumber\" expr=\"'%s'\"/>" % (cellnum))

    self.response.out.write("<var name=\"choose_port\" expr=\"%s\"/>" % (nearest_port))

    self.response.out.write("""
<log expr="'choose_port:' + choose_port"/>
""")

    self.response.out.write("""
<field  cond="ask_for_zip == '1'" name="zip_code" type="digits?length=5" bargein="false">
<prompt>
Please key in your 5 digit zip code. This will enable us to 
find the nearest tide reporting station.
</prompt>

<filled>
</filled> 

</field>

""")

    self.response.out.write("""
<subdialog  cond="ask_for_zip == '1'" name="local_tides" src="http://robocal1.appspot.com/show_tides"  namelist="zip_code cellnumber"  method = "get" >
</subdialog>
""")
    self.response.out.write("""
<subdialog  cond="ask_for_zip != '1'" name="local_tides1" src="http://robocal1.appspot.com/show_tides"  namelist="cellnumber choose_port"  method = "get" >
</subdialog>
""")

      
    if (0):
      self.response.out.write("""
bulkload_client.py --filename maybe_even_better.csv --kind Port --url http://localhost:8080/load<subdialog  name="local_tides" src="http://robocal1.appspot.com/show_tides" method = "get" >
""")
      self.response.out.write("<param name=\"cellnumber\" expr =\"'%s'\" /> " % cellnum)
      if (nearest_port > 0):
        self.response.out.write("<param name=\"choose_port\" expr=\"'%s'\" />" % nearest_port)
      if (ask_for_zip == 1):
        self.response.out.write("<param name=\"zip_code\" expr=\"zip_code\" />")

      self.response.out.write("</subdialog>")

## foo start
    self.response.out.write("""
 <field  name="new_port" type="boolean" >
 <property name="bargein" value="true"/>
<!--   <property name="inputmodes" value="dtmf"/> -->

  <prompt>
Press 1 if you want to change the zip code the tide is calculated from.
Otherwise, bye bye!
  </prompt>
<filled>
<if cond="new_port">
   <assign name="ask_for_zip" expr="'1'"/>
</if>
</filled>

</field>
""")

## foo end
    self.response.out.write("""

</form>


</vxml>
""")


class LatLng(webapp.RequestHandler):
  def get(self, my_address):
#    my_address = "Bar+Harbor,+Maine"
    key = "ABQIAAAArbyRqgj0_bOIl5_5MGyneRSss0KkgIHkkLqBbqSrQFXluxx97RTSPD_tqRvlVT8lrFqOX78M9gJKQA"
    address = "http://maps.google.com/maps/geo?q=%s&output=json&key=%s" % (my_address, key)
#    self.response.out.write("address: %s" % (address))
    result = urlfetch.fetch(address)
    if result.status_code == 200:
      json = result.content
      parsed = simplejson.loads(json)
      placemark = parsed['Placemark'][0]
      point = placemark['Point']
      coords = point['coordinates']
      self.response.out.write("Lat: %.4f Lng: %.4f" % (coords[0], coords[1]))


class Port(db.Model):
  number = db.StringProperty(required=True)
  name = db.StringProperty(required=True)
  lat = db.FloatProperty(required=True)
  lng = db.FloatProperty(required=True)
  good_data =  db.BooleanProperty()
  int_good_data =  db.IntegerProperty()

class PortDeleter(webapp.RequestHandler):
  def get(self):
    query = Port.all()
    for port in query:
      port.delete()

          

class PortSearcher(webapp.RequestHandler):
  def get(self):
    # We use the webapp framework to retrieve the keyword
    keyword = self.request.get('keyword')

    self.response.headers['Content-Type'] = 'text/plain'
    if not keyword:
      self.response.out.write("No keyword has been set")
    else:
      # Search the 'Port' Entity based on our keyword
      query = search.SearchableQuery('Port')
      query.Search(keyword)
      for result in query.Run():
         self.response.out.write('%s %s %s' % 
                                 (result['name'], result['lat'], result['lng']))

class PortShower(webapp.RequestHandler):
  def get(self):
    query = Port.all()
    query.filter('int_good_data =', 1)
    self.response.out.write("""<?xml version="1.0" encoding="UTF-8" ?> 
<points>
""")
    for port in query:
      lat = port.lat
      lng = port.lng
      name = port.name
      number = port.number

      self.response.out.write("""
<point lat="%.4f" lng="%.4f" name="%s" number="%s"></point>
""" % (lat, lng, name, number))
    self.response.out.write("""
</points>
""")


class PortMapper(webapp.RequestHandler):


  def get(self):
    self.response.out.write("""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
    <title>Google Maps JavaScript API Example</title>
    <script src="http://maps.google.com/maps?file=api&amp;v=2&amp;key=ABQIAAAArbyRqgj0_bOIl5_5MGyneRTW4rlniwbXh5g83cEBdJcSPFSiExQa_HK10yOJXHuLcus8w5zAOsIVjA"
      type="text/javascript"></script>
    <script type="text/javascript">

    //<![CDATA[

    var map;
   var gmarkers = [];	  
    var geocoder = null;
    var last_overlay;
    var last_point;
    var start_point;
    var start_overlay;
    var geocoder = null;


    function load() {
      if (GBrowserIsCompatible()) {
        var side_bar_html = "";
        map = new GMap2(document.getElementById("map"));
        map.setCenter(new GLatLng(40.4782, -98.5254), 3);
        map.setMapType(G_HYBRID_MAP);
        // map.addControl(new GSmallMapControl());
        map.addControl(new GLargeMapControl());
        map.addControl(new GMapTypeControl());

       init_tide_stations();

       geocoder = new GClientGeocoder();


      }
    }

    function init_tide_stations(){

	var url = "/port_shower";

	GDownloadUrl(url, function(data, responseCode) {
		side_bar_html  = '<table>';
		var xml = GXml.parse(data);
		//		console.log ("xml: %s", xml);
		var points = xml.documentElement.getElementsByTagName("point");
		if (1){
		    for (var i = 0; i < points.length; i++) {
			var point = points[i];
			var name  = point.getAttribute("name");
			var lat  = point.getAttribute("lat");
			var lng  = point.getAttribute("lng");
			var number  = point.getAttribute("number");
			var marker =  create_a_marker (point, i);
                        gmarkers[i] = marker;

//			side_bar_html += '<tr>' + '<td>' + '<a href="javascript:mydrag(' + i + ')">' + name + '</a>' + '</td>' + '</tr>';
			side_bar_html += '<tr>' + '<td>' + '<a href="javascript:mydrag(' + i + ')">' + name + '</a>' + '</td>' + '</tr>';
//			side_bar_html += '<tr>' + '<td>' +  '<a href="http://tidesonline.nos.noaa.gov/data_read.shtml?station_info=' + number + '"' + 'target="top">' + name + '</a>' + '</td>' + '</tr>';

		    }
		}
		side_bar_html += '</table>';
		// put the assembled side_bar_html contents into the side_bar div
//		document.getElementById("side_bar").innerHTML = side_bar_html;

	    }
	    );
    }

function mydrag(i) {
  GEvent.trigger(gmarkers[i], "dragstart");
      }

function myclick(i) {
  GEvent.trigger(gmarkers[i], "click");
}

function create_a_marker (point, i){

    var lat  = point.getAttribute("lat");
    var lng  = point.getAttribute("lng");
    var name  = point.getAttribute("name");
    var number  = point.getAttribute("number");
    var latlng = new GLatLng(lat, lng);
    var marker = new GMarker(latlng);
    map.addOverlay(marker);
    marker.setImage('http://labs.google.com/ridefinder/images/mm_20_yellow.png');
// Listener
   if (0){
    GEvent.addListener(marker, "click", function() {
    var myHtml = "<p>" + '<a href="http://tidesonline.nos.noaa.gov/data_read.shtml?station_info=' + number + '">' + name + '</a>';
//      var url = new Url(); 
//      var myHtml = url.fetch('http://tidesonline.nos.noaa.gov/data_read.shtml?station_info=' + number);
    map.openInfoWindowHtml(latlng, myHtml);
//    map.showMapBlowup(latlng);
          });
}

   if (1){
    GEvent.addListener(marker, "click", function() {
        var url = '/show_tides?choose_port=' + number + '&mode=table';
	GDownloadUrl(url, function(data, responseCode) {
                map.openInfoWindowHtml(latlng, data);
}
 );
         });
}

   if (1){
    GEvent.addListener(marker, "dragstart", function() {
 //   map.showMapBlowup(latlng);
      map.setCenter(point, 8);
// marker.showMapBlowup({zoomLevel:9}); 
}
 );

}
return marker;
}

 
function showAddress(address) {
	 var have_good_address;
      if (geocoder) {
        geocoder.getLatLng(
          address,
          function(point) {
            if (!point) {
              alert(address + " not found");
            } else {
              
              have_good_address = 1;
              map.setCenter(point, 8);
     	      last_point = point;
              if (last_overlay){
	  map.removeOverlay(last_overlay);
	  }
    var marker = new GMarker(point);
     	 last_overlay = marker;

         map.addOverlay(marker);		
//         marker.setImage ('http://maps.google.com/mapfiles/kml/pal3/icon52.png');
         marker.setImage ('http://labs.google.com/ridefinder/images/mm_20_green.png');
            }

          }
	  
        );
      }

    }

function showTideStation(zip_code) {
  if (! validateZIP (zip_code)){
        return;
        }
	var url = "/zip_decoder?zip_code=" + zip_code;

	GDownloadUrl(url, function(data, responseCode) {
		var xml = GXml.parse(data);
		//		console.log ("xml: %s", xml);
		var points = xml.documentElement.getElementsByTagName("point");
                var point = points[0];
                var name  = point.getAttribute("name");
                var lat1  = parseFloat (point.getAttribute("lat1"));
                var lng1  = parseFloat (point.getAttribute("lng1"));
                var latlng1 = new GLatLng(lat1, lng1);
                var marker1 = new GMarker(latlng1);

                var lat2  = parseFloat (point.getAttribute("lat2"));
                var lng2  = parseFloat (point.getAttribute("lng2"));
                var latlng2 = new GLatLng(lat2, lng2);
                var marker2 = new GMarker(latlng2);

//                alert ("Here is a nice name, lat,lng :" + name + " lat1 " + lat1 + " lng1 " + lng1 + " lat2 " + lat2  + " lng2 " + lng2);
//                map.setCenter(latlng, 9);
		if (1){
		    var distance = latlng1.distanceFrom(latlng2);
                    distance = distance / 1609.344;
//		    alert ("distance: " + distance);
//		    distance = 10;
              if (last_overlay){
	  map.removeOverlay(last_overlay);
	  }

                map.addOverlay(marker1);		
                marker1.setImage ('http://labs.google.com/ridefinder/images/mm_20_green.png');
                last_overlay = marker1;
		map.setCenter(new GLatLng(lat2, lng2), 8); 

               drawCircle(lat2, lng2, distance, "#000080", 1, 0.75, "#0000FF",.5);   
		}
		if (0){
		    lat3 = 53.479874;
		    lng3 = -2.246704;
                map.setCenter(new GLatLng(lat3, lng3), 9); 
        drawCircle(lat3, lng3, 10.0, "#000080", 1, 0.75, "#0000FF",.5);   
		}
	       if (0){
                map.addOverlay(marker1);		
                marker1.setImage ('http://labs.google.com/ridefinder/images/mm_20_green.png');
                map.addOverlay(marker2);		
                marker2.setImage ('http://labs.google.com/ridefinder/images/mm_20_green.png');


                drawCircle(marker1, marker2, "#F0F0F0", "#F0F0F0");
//                map.addOverlay(marker);
	       }
                
                }
);
}

function drawCircleNoWork(centerMarker, radiusMarker, borderColour, fillColour) {
    var normalProj = map.getCurrentMapType().getProjection();
    // var zoom = map.getZoom();
    var zoom = 8;
    var centerPt = normalProj.fromLatLngToPixel(centerMarker, zoom);
      var radiusPt = normalProj.fromLatLngToPixel(radiusMarker, zoom);
      var circlePoints = Array();

    with (Math) {
        var radius = floor(sqrt(pow((centerPt.x-radiusPt.x),2) +
pow((centerPt.y-radiusPt.y),2)));

       for (var a = 0 ; a < 361 ; a+=5 ) {
           var aRad = a*(PI/180);
           y = centerPt.y + radius * sin(aRad)
           x = centerPt.x + radius * cos(aRad)
           var p = new GPoint(x,y);
           circlePoints.push(normalProj.fromPixelToLatLng(p, zoom));
           }
           circleLine2 = new GPolygon(circlePoints,borderColour,0, 0,
fillColour,0.5);
           map.addOverlay(circleLine2);

    }
}

 function drawCircle(lat, lng, radius, strokeColor, strokeWidth, strokeOpacity, fillColor, fillOpacity) {
      var d2r = Math.PI/180;
      var r2d = 180/Math.PI;
      var Clat = radius * 0.014483;  // Convert statute miles into degrees latitude
      var Clng = Clat/Math.cos(lat*d2r); 
      var Cpoints = []; 
      for (var i=0; i < 33; i++) { 
        var theta = Math.PI * (i/16); 
        Cy = lat + (Clat * Math.sin(theta)); 
        Cx = lng + (Clng * Math.cos(theta)); 
        var P = new GPoint(Cx,Cy); 
        Cpoints.push(P); 
      }

      var polygon = new GPolygon(Cpoints, strokeColor, strokeWidth, strokeOpacity, fillColor, fillOpacity);
      map.addOverlay(polygon);
     }

function validateZIP(field) {
var valid = "0123456789-";
var hyphencount = 0;

if (field.length!=5 && field.length!=10) {
alert("Please enter your 5 digit or 5 digit+4 zip code.");
return false;
}
for (var i=0; i < field.length; i++) {
temp = "" + field.substring(i, i+1);
if (temp == "-") hyphencount++;
if (valid.indexOf(temp) == "-1") {
alert("Invalid characters in your zip code.  Please try again.");
return false;
}
if ((hyphencount > 1) || ((field.length==10) && ""+field.charAt(5)!="-")) {
alert("The hyphen character should be used with a properly formatted 5 digit+four zip code, like '12345-6789'.   Please try again.");
return false;
   }
}
return true;
}

function ptdistance (lat1, long1, lat2, long2){
    var R = 6371; // km
    var dLat = (lat2-lat1).toRad();
    var dLon = (lon2-lon1).toRad(); 
    var a = Math.sin(dLat/2) * Math.sin(dLat/2) +
        Math.cos(lat1.toRad()) * Math.cos(lat2.toRad()) * 
        Math.sin(dLon/2) * Math.sin(dLon/2); 
    var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a)); 
    var d = R * c;
}




   //]]>
    </script>
  </head>
  <body onload="load()" onunload="GUnload()">
    <table border=1>
      <tr>
        <td>
    <div id="map" style="width: 450px; height: 450px"></div>
        </td>
        <td width = 450px valign="top">
<div id="side_bar" style="overflow:auto; height:450px;">
<p>
Welcome to <strong>TideSpot.com</strong>, a mobile application to deliver your
local tide information. On the map to the left, you see the locations of all the tide stations that TideSpot uses.
<p>
To use <strong>TideSpot.com</strong>, call 617-830-4676 (<a href="skype:+99000936 9996076980?call">Or try it with Skype!</a>).. The first time you call, you'll 
be asked for you local zip code. We'll figure out where the nearest NOAA tide station is, and read you the information.
<p> 
Your location is "sticky", so you won't be asked for your zip code after that
first call. However, after hearing the tide, during any given session,
you'll be given the opportunity to change your zip code setting.
<p>
You can keep up with TideSpot.com developments by following my <a href="http://tidespot.blogspot.com/">blog</a>.
</div>
        </td>

</tr>
</table>

""")
    self.response.out.write("""
<FORM NAME="myform" ACTION="" METHOD="GET">

<p style="text-indent: 80px">
<input type="text" size="60" name="address" value="" />
<input type="button" name="Go" value="Test your zip code here" onClick="showTideStation(myform.address.value); return false"/>

  </body>
</html>
""")

class MainPage(webapp.RequestHandler):
   def get(self):
     self.response.out.write("""
<p>
Welcome to <strong>TideSpot.com</strong>, a mobile application to deliver your
local tide information.
<p>
To use <strong>TideSpot.com</strong>, call 617-830-4676 (<a href="skype:+99000936 9996076980?call">Or try it with Skype!</a>).. The first time you call, you'll 
be asked for you local zip code. We'll figure out where the nearest NOAA tide station is, and read you the information.
<p> 
Your location is "sticky", so you won't be asked for your zip code after that
first call. However, after hearing the tide, during any given session,
you'll be given the opportunity to change your zip code setting.
<p>
Go <a href="/port_mapper">here</a> to see a map of all the tide stations.
<p>
You can keep up with TideSpot.com developments by following my <a href="http://tidespot.blogspot.com/">blog</a>.
""")

