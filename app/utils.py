# Copyright 2010 Google
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

"""Utility functions common to all handlers."""

__author__ = 'Ka-Ping Yee <kpy@google.com>'

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
import cgitb
import crypto
import google.appengine.ext.webapp.template
import google.appengine.ext.webapp.util
import latitude
import logging
import model
import oauth
import os
import re
import simplejson
import sys
import urllib
from google.appengine.api import users


ROOT = os.path.dirname(__file__)



class ErrorMessage(Exception):
    """Raise this exception to show an error message to the user."""
    def __init__(self, status, message):
        self.status = status
        self.message = message


class Redirect(Exception):
    """Raise this exception to redirect to another page."""
    def __init__(self, url):
        self.url = url


class Handler(webapp.RequestHandler):
    def render(self, path, **params):
        """Renders the template at the given path with the given parameters."""
        self.write(webapp.template.render(os.path.join(ROOT, path), params))

    def write(self, text):
        """Writes the body of the HTTP reply."""
        self.response.out.write(text)

    def initialize(self, request, response):
        """Sets up useful handler variables for every request."""
        webapp.RequestHandler.initialize(self, request, response)
        self.user = users.get_current_user()
        self.member = model.Member.get(users.get_current_user())
        if self.user:
            self.xsrf_key = model.Config.get_or_generate('xsrf_key')

        # Populate self.vars with useful variables for templates.
        agent = request.headers['User-Agent']
        is_mobile = re.search('iPhone|Android', agent) or request.get('mobile')
        self.vars = {'user': self.user, 'member': self.member,
                     'login_url': users.create_login_url(request.uri),
                     'logout_url': users.create_logout_url(request.uri),
                     'is_mobile': is_mobile}

    def set_signature(self, lifetime=None):
        """Generates a signature to prevent XSRF (a confused deputy attack)."""
        self.vars['signature'] = crypto.sign(
            self.xsrf_key, self.user.user_id(), lifetime)

    def verify_signature(self):
        """Verify that the incoming request includes a valid signature."""
        if not crypto.verify(
            self.xsrf_key, self.user.user_id(), self.request.get('signature')):
            raise ErrorMessage(400, 'Invalid signature.')

    def require_user(self):
        """Ensures that the user is logged in."""
        if not self.user:
            raise Redirect(users.create_login_url(self.request.uri))

    def require_member(self):
        """Ensures that the user has registered and authorized this app."""
	logging.info ("require_member next will be %s" % (self.request.uri))
        if not self.member:
            raise Redirect('/_register?' + urlencode(
                next=self.request.uri, duration=self.request.get('duration')))

    def handle_exception(self, exception, debug_mode):
        """Adds special exception handling for Redirect and ErrorMessage."""
        if isinstance(exception, Redirect):  # redirection
            self.redirect(exception.url)
        elif isinstance(exception, ErrorMessage):  # user-facing error message
            self.error(exception.status)
            self.response.clear()
            self.render('templates/error.html', message=exception.message)
        else:
            self.error(500)
            logging.exception(exception)
            if debug_mode:
                self.response.clear()
                self.write(cgitb.html(sys.exc_info()))


def describe_delta(delta):
    seconds = delta.days * 24 * 3600 + delta.seconds
    minutes = round(seconds/60.0)
    hours = round(minutes/60.0)
    if minutes < 60:
        return '%d min' % minutes
    else:
        return '%d h' % hours


def urlencode(*args, **kwargs):
    """A shorthand for urllib.urlencode that uses keyword arguments."""
    return urllib.urlencode(kwargs)


def clean_tag(tag):
    """Normalizes a tag to a plain lowercase identifier."""
    return re.sub('[^A-Za-z0-9]', '', tag).lower()


def get_location(member):
    """Gets a user's location as a db.GeoPt, using the Latitude API."""
    token = oauth.OAuthToken(member.latitude_key, member.latitude_secret)
    client = latitude.LatitudeOAuthClient(oauth_consumer, token)
    result = latitude.Latitude(client).get_current_location()
    data = simplejson.loads(result.content)['data']
    if 'latitude' in data and 'longitude' in data:
        return db.GeoPt(data['latitude'], data['longitude'])


def run(*args, **kwargs):
    """Creates and runs a webapp application."""
    webapp.util.run_wsgi_app(webapp.WSGIApplication(*args, **kwargs))
