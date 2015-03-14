# Introduction #

If the user is carrying a smart phone, like an iPhone, an Android device, or a Blackberry, Google Latitude can continually update his location.  Alternatively, the user can simulate this movement by moving his avatar around a Google Map from the  iGoogle home page.

The crucial call to Google Latitude is
```
result = latitude.Latitude(client).get_current_location()
```

However, this one line is deceptively simple, because the _client_ object encapsulates the fact that a user has authenticated Moveable Weather to acccess the Latitude data. For that authentication, we need OAuth.

# Details #

We really don't have to concern ourselves much with the intricacies of of the "oauth dance", because engineers at Google have provided a very [helpful demo](https://groups.google.com/group/google-latitude-api/browse_thread/thread/2556e289d98def0c/31ca0d93309eae14?lnk=gst&q=ping#31ca0d93309eae14), containing the necessary Python code. In Moveable Weather, this code is embodied here:

  * [oauth.py](http://code.google.com/p/moveable-weather/source/browse/trunk/app/oauth.py)
  * [oauth\_appengine.py](http://code.google.com/p/moveable-weather/source/browse/trunk/app/oauth_appengine.py)
  * [oauth\_webapp.py](http://code.google.com/p/moveable-weather/source/browse/trunk/app/oauth_webapp.py)