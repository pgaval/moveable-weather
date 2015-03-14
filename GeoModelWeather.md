# Introduction #


Once we have uploaded our zip code CSV file to Moveable Weather, we need to arrange for this data to be indexed so we can do "proximity searches". Otherwise, we wouldn't have a way of associating geospatial information coming in from Google Latitude with actual zip codes.

The first step is to define a data model, called ZipCode, which conforms to the data in the CSV file, but which also inherits from [GeoModel](http://pypi.python.org/pypi/geomodel/0.2.0).

```
class ZipCode(GeoModel):
  """A location-aware model for zip codes

  """
  zip = db.StringProperty(required=True)
  city = db.StringProperty(required=True)
  state = db.StringProperty(required=True)
  latitude = db.FloatProperty(required=True)
  longitude = db.FloatProperty(required=True)
  has_location = db.IntegerProperty(required=True)
  timezone =  db.IntegerProperty()
  dst = db.IntegerProperty()


```


Once this data is uploaded, it still needs to be indexed. This is done by calling the `update_location` method on each ZipCode data record.

It may seem like the straightforward approach is to define a function that simply loops through all the record in the data model, calling `upload_location` on each one. But such an approach won't work, because App Engine has a restriction limiting each url invocation.

The workaround I have come up with for Moveable Weather is to define a GET method on a class UpdateLocations that updates a batch of locations, and then uses memcache to remember where it left off. I had to experiment a bit to determine what size batch it was happy with, but having done that, I just ran an infinite loop in the shell that repeately invoked this url, via a "make" target:

```
while (1)
   make fill LIMIT=100
```

The GET method in UpdateLocations reports on its progress, and eventually reports that it isn't changing any records. At that point, you can just break out of the loop, in the shell.



Here's the crucial call

> zip\_records = model.ZipCode.proximity\_fetch(
> > model.ZipCode.all(),  # Rich query!
> > geo.geotypes.Point(lat, lng),  # Or db.GeoPt
> > max\_results=10,
> > max\_distance=16000)  # Within 100 miles.