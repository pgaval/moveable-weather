# Process Flow #

  1. Users sign up by going to http://moveable-weather.appspot.com.
  1. They are guided through the [oauth dance](http://code.google.com/apis/gdata/articles/oauth.html), for Google Latitude.
  1. They are issued an 8 digit password.
  1. They call the Moveable Weather access number and are prompted to enter their password.
  1. Each subsequent time they call, based on their Google Latitude current location,
    1. they will be read the local weather
    1. The can then "travel to a new location", and hit any key, to again be read the weather, or they can hang up

> Note: For demo purposes, they can "travel to a new location" by moving their avatar to a new location on the map, inside the Google Latitude gadget on their [iGoogle home page](http://m.google.com/latitude?dc=lato).