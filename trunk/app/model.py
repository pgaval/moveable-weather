# Copyright 2010 Google Inc.
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

__author__ = 'Ka-Ping Yee <kpy@google.com>'

from google.appengine.ext import db
import datetime
import random
import logging
from geo.geomodel import GeoModel


class Member(db.Model):
    """Represents a user who has registered and authorized this app.
    key_name: user.user_id()"""
    user = db.UserProperty()
    nickname = db.StringProperty()  # nickname to show with the user's location
    latitude_key = db.StringProperty()  # OAuth access token key
    latitude_secret = db.StringProperty()  # OAuth access token secret
    location = db.GeoPtProperty()  # user's geolocation
    location_time = db.DateTimeProperty()  # time that location was recorded
    #password = db.StringProperty()  # 8 digit password
    passw = db.StringProperty()  # 8 digit password
    cellnumber = db.PhoneNumberProperty(required=False)

    logging.info ("user: %s latitude_key: %s latitude_secret: %s location: %s" % (user, latitude_key, latitude_secret, location))


    @staticmethod
    def get_for_tag(tag, now):
        """Gets all active members of the given tag."""
        members = Member.all().filter('tags =', tag).fetch(1000)
        results = []
        for member in members:
            tag_index = member.tags.index(tag)
            stop_time = member.stop_times[tag_index]
            if stop_time > now:
                results.append(member)
        return results

    @staticmethod
    def create(user):
        """Creates a Member object for a user."""
	logging.info ("I am creating a member")
        return Member(key_name=user.user_id(), user=user)

    @staticmethod
    def get(user):
        """Gets the Member object for a user."""
        if user:
            return Member.get_by_key_name(user.user_id())

    def find_member(self, id):
        try:
            users =  Member.all().filter('id =', identifier)
            user = users[0]
        except:
            logging.info ("I came up with nothing")
            user = ""
        return user




    @staticmethod
    def join(user, tag, stop_time):
        """Transactionally adds a tag for a user."""
        def work():
            member = Member.get(user)
            member.remove_tag(tag)
            member.tags.append(tag)
            member.stop_times.append(stop_time)
            member.put()
        db.run_in_transaction(work)

    @staticmethod
    def quit(user, tag):
        """Transactionally removes a tag for a user."""
        def work():
            member = Member.get(user)
            member.remove_tag(tag)
            member.put()
        db.run_in_transaction(work)

    def clean(self, now):
        """Transactionally removes all expired tags for this member."""
        def work():
            member = db.get(self.key())
            index = 0
            while index < len(member.tags):
                if member.stop_times[index] <= now:
                    # We don't bother to update member_count here;
                    # update_tagstats will eventually take care of it.
                    member.remove_tag(member.tags[index])
                else:
                    index += 1
            member.put()
            return member
        # Before starting a transaction, test if cleaning is needed.
        if self.stop_times and min(self.stop_times) <= now:
            return db.run_in_transaction(work)
        return self

    def set_location(self, location, now):
        """Transactionally sets the location for this member."""
        def work():
            member = db.get(self.key())
            member.location = location
            member.location_time = now
            member.put()
        db.run_in_transaction(work)


class ZipCode(GeoModel):
  """A location-aware model for zip codes

  """
  zip = db.StringProperty(required=True)
  city = db.StringProperty(required=True)
  state = db.StringProperty(required=True)
  latitude = db.FloatProperty(required=True)
  longitude = db.FloatProperty(required=True)
  has_location = db.IntegerProperty(required=True)
  timezone =  db.IntegerProperty()
  dst = db.IntegerProperty()

class Port(GeoModel):
  """A location-aware model for coastal Ports

  """
  port = db.StringProperty(required=True)
  place = db.StringProperty(required=True)
  latitude = db.FloatProperty(required=True)
  longitude = db.FloatProperty(required=True)
  has_location = db.IntegerProperty(required=True)
  good_data =  db.IntegerProperty(required=False)
  cleaned =  db.IntegerProperty(required=False)

class NRHP(GeoModel):
  """A location-aware model for coastal Ports

  """
  title = db.StringProperty(required=True)
  place = db.StringProperty(required=False)
  refnum = db.StringProperty(required=True)
  latitude = db.FloatProperty(required=True)
  longitude = db.FloatProperty(required=True)
  has_location = db.IntegerProperty(required=True)

