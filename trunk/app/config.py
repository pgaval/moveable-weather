# To set up this application as an OAuth consumer:
# 1. Go to https://www.google.com/accounts/ManageDomains
# 2. Follow the instructions to register and verify your domain
# 3. The administration page for your domain should now show an "OAuth
#    Consumer Key" and "OAuth Consumer Secret".  Put these values into
#    the app's datastore by calling Config.set('oauth_consumer_key', ...)
#    and Config.set('oauth_consumer_secret', ...).

from google.appengine.ext import db
import oauth

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


