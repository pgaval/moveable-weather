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

"""Steps of the OAuth dance implemented for the webapp framework."""

__author__ = 'Ka-Ping Yee <kpy@google.com>'

import oauth
import oauth_appengine
import logging

def redirect_to_authorization_page(
    handler, oauth_client, callback_url, parameters):
    """Sends the user to an OAuth authorization page."""
    # Get a request token.
    helper = oauth_appengine.OAuthDanceHelper(oauth_client)
    logging.info ("callback_url %s parameters: %s" % (callback_url, parameters))
    request_token = helper.GetRequestToken(callback_url, parameters)

    # Save the request token in cookies so we can pick it up later.
    handler.response.headers.add_header(
        'Set-Cookie', 'request_key=' + request_token.key)
    handler.response.headers.add_header(
        'Set-Cookie', 'request_secret=' + request_token.secret)

    # Send the user to the authorization page.
    handler.redirect(
        helper.GetAuthorizationRedirectUrl(request_token, parameters))


def handle_authorization_finished(handler, oauth_client):
    """Handles a callback from the OAuth authorization page and returns
    a freshly minted access token."""
    # Pick up the request token from the cookies.
    request_token = oauth.OAuthToken(
        handler.request.cookies['request_key'],
        handler.request.cookies['request_secret'])

    # Upgrade our request token to an access token, using the verifier.
    helper = oauth_appengine.OAuthDanceHelper(oauth_client)
    access_token = helper.GetAccessToken(
        request_token, handler.request.get('oauth_verifier', None))

    # Clear the cookies that contained the request token.
    handler.response.headers.add_header('Set-Cookie', 'request_key=')
    handler.response.headers.add_header('Set-Cookie', 'request_secret=')

    return access_token
