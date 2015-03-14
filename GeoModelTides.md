# Introduction #

Once we have uploaded our tides code CSV file to Moveable Weather, we need to arrange for this data to be indexed so we can do "proximity searches". Otherwise, we wouldn't have a way of associating geospatial information coming in from Google Latitude with actual tide reporting stations.

The first step is to define a data model, called Port, which conforms to the data in the CSV file, but which also inherits from [GeoModel](http://pypi.python.org/pypi/geomodel/0.2.0).

```
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


```


Once this data is uploaded, it still needs to be indexed. This is done by calling the `update_location` method on each Port data record.

It may seem like the straightforward approach is to define a function that simply loops through all the records in the data model, calling `port_locations_update` on each one. But such an approach won't work, because App Engine has a restriction limiting each url invocation.

The workaround I have come up with for Moveable Weather is to define a GET method on a class UpdatePortLocations that updates a batch of locations, and then uses memcache to remember where it left off. I had to experiment a bit to determine what size batch it was happy with, but having done that, I just ran an infinite loop in the shell that repeately invoked this url, via a "make" target:

```
while (1)
   make port_fill LIMIT=20
```

The GET method in UpdateLocations reports on its progress, and eventually reports that it isn't changing any records. At that point, you can just break out of the loop, in the shell.

## Cleaning Out the Ports that Don't Have Tide Data ##

There's one more step. This is necessary because not all the tide stations actually have tidal data. Some of them come up blank. So we do a bit of preprocessing, looping through each tide station to see if it contains a tidal table. We then mark the row of data, setting a field called "good\_data" to either 1 or 0. Again, just like the previous step, we perform this operation by doing a loop from our command prompt.
```
        while (1)
            make clean_ports LIMIT=20 CURSOR_NAME=my_port_cleaner_cursor3
```