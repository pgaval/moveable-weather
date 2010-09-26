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

"""Request handlers for the OAuth authorization process."""

__author__ = 'Ka-Ping Yee <kpy@google.com>'

from google.appengine.ext import db
import datetime
import latitude
import model
import oauth
import oauth_webapp
import utils
import logging


class RegisterHandler(utils.Handler):
    """Registration and Latitude API authorization for new users."""

    def get(self):
        self.require_user()
        nickname = self.request.get('nickname', '')
        next = self.request.get('next', '')
#        duration = utils.describe_delta(
#            datetime.timedelta(0, int(self.request.get('duration', '0'))))
        duration = 30
        if not nickname:
	    logging.info ("No nickname")
            self.render('templates/register.html', next=next, duration=duration,
                        nickname=self.user.nickname().split('@')[0])
        else:
            # Then proceed to the OAuth authorization page.
	    logging.info ("Yes nickname: %s" % nickname)
            parameters = {
                'scope': latitude.LatitudeOAuthClient.SCOPE,
                'domain': model.Config.get('oauth_consumer_key'),
                'granularity': 'best',
                'location': 'current'
            }
            callback_url = self.request.host_url + '/_oauth_callback?' + \
                utils.urlencode(nickname=nickname, next=next)
            oauth_webapp.redirect_to_authorization_page(
                self, latitude.LatitudeOAuthClient(utils.oauth_consumer),
                callback_url, parameters)


class OAuthCallbackHandler(utils.Handler):
    """Handler for the OAuth callback after a user has granted permission.""" 

    def get(self):
        self.require_user()
        next = self.request.get('next', '')
        access_token = oauth_webapp.handle_authorization_finished(
            self, latitude.LatitudeOAuthClient(utils.oauth_consumer))

        # Store a new Member object, including the user's current location.
        member = model.Member.create(self.user)
        member.nickname = self.request.get('nickname')
        member.latitude_key = access_token.key
        member.latitude_secret = access_token.secret
        member.location = utils.get_location(member)
        member.location_time = datetime.datetime.utcnow()
        if not member.location:
            raise utils.ErrorMessage(400, '''
Sorry, Google Latitude has no current location for you.
''')
        member.put()
        logging.info ("location: %s" % member.location)
	memmie = model.Member.get(self.user)
        logging.info ("memmie location: %s" % memmie.location)
        self.render('templates/show_location.html', location=member.location, vars=vars)

#        raise utils.Redirect(next or '/')


if __name__ == '__main__':
    utils.run([
        ('/_register', RegisterHandler),
        ('/_oauth_callback', OAuthCallbackHandler)
    ])
