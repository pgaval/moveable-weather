#!/usr/bin/env python
#
# Copyright 2008 Google Inc.
# Copyright 2010 Joe LaPenna
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
#

"""Latitude OAuth client."""


import oauth
import oauth_appengine


class LatitudeOAuthClient(oauth_appengine.OAuthClient):
    """Latitude-specific OAuth client.

    Per: http://code.google.com/apis/gdata/articles/oauth.html
    """

    REQUEST_TOKEN_URL = 'https://www.google.com/accounts/OAuthGetRequestToken'
    ACCESS_TOKEN_URL = 'https://www.google.com/accounts/OAuthGetAccessToken'
    AUTHORIZATION_URL = \
        'https://www.google.com/latitude/apps/OAuthAuthorizeToken'
    SCOPE = 'https://www.googleapis.com/auth/latitude'

    def __init__(self, oauth_consumer=None, oauth_token=None):
        super(LatitudeOAuthClient, self).__init__(
            oauth_consumer=oauth_consumer,
            oauth_token=oauth_token,
            request_token_url=LatitudeOAuthClient.REQUEST_TOKEN_URL,
            access_token_url=LatitudeOAuthClient.ACCESS_TOKEN_URL,
            authorization_url=LatitudeOAuthClient.AUTHORIZATION_URL)
        self.signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()


class Latitude(object):
    """API access to Latitude."""

    REST_URL = 'https://www.googleapis.com/latitude/v1/%s'

    def __init__(self, oauth_client):
        self.client = oauth_client

    def get_current_location(self):
        request = oauth.OAuthRequest.from_consumer_and_token(
            self.client.get_consumer(),
            token=self.client.get_token(),
            http_method='GET',
            http_url=Latitude.REST_URL % ('currentLocation',),
            parameters={'granularity': 'best'})

        request.sign_request(
            self.client.signature_method,
            self.client.get_consumer(),
            self.client.get_token())

        return self.client.access_resource(request)
