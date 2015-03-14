# Introduction #

We use the [Google Weather API](http://blog.programmableweb.com/2010/02/08/googles-secret-weather-api/) in Moveable Weather, because it is simple, non-metered, and free. The API can accept urls using place names or Zip Codes:

  * http://www.google.com/ig/api?weather=Mountain+View
  * http://www.google.com/ig/api?weather=03801

The data coming from Google Latitude is in terms of latitude and longitude, and elsewhere we describe our technique for resolving this data to the nearest zip code. So it's these zip codes that we pass to Google Weather.

The data coming back from the Google Weather API is xml, and thus easy to parse. We parse this xml into a Python dictionary, which is easy to pass around. The voice interface picks out items from this dictionary, and then reports the weather like this:

```
 trop.say ("%s,%s. Weather condition: %s. Temperature: %s.  Wind: %s." % (city, state1, condition, temp_f, wind))
```