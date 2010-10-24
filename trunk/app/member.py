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

OAUTH_CALLBACK_PATH = '/oauth_callback'
GOOGLE_VERIFY_PATH = "/%s" % my_globals.GOOGLE_VERIFY_FILE
ROOT = os.path.dirname(__file__)

class Membership (webapp.RequestHandler):

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


