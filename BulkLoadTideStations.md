# Introduction #

The better.csv file, [freely available, here, in slighlty different form](http://opendap.co-ops.nos.noaa.gov/ioos-dif-sos/get/getcapabilities/nwlonstations.jsp), has been altered slightly, for use with Moveable Tides. An extra field, called `has_location` has been added to the end of each line. Initially, the value of this field is set to `0` for each line. After you upload the `better.csv` file, you will need to loop through each record in this data, calling a special method called `update_location`. The purpose of this method, inherited from the `GeoName` class, is to ensure that each latitude/longitude pair is stored in a _geohash_. This will enable _proximity searches_, which are critical.

The reason proximity searches are necessary is that each tide station in the database is associated with a partilar latitude/longitude pair which we can thing of as occupying a location along the coast. But data about a user's location, coming in via Google Latitude, will be arbitrary, and thus, we'll need to be able to compute which tide station's "neighborhood" it falls within. This is what a proximity search is.

# Details #

Here are the steps to use bulk upload to upload the tide station data.

  1. From the  `app` directory, issue the command:
```
     make upload_ports
```
  1. Next, we need to make sure the `upload_location` method gets called on each of our newly minted Port objects. What we want to do is loop through all the items in the Port data store, but doing so in one go will cause App Engine to time out. So the solution we adopt here is to invoke a custom GET method that will update the tide stations in batches, and set it up so that it is careful to save its place at the end of each call. Fortunately, App Engine supports _cursors_ for just this purpose.
  1. All that remains is to invoke this GET method, repeatedly, until all tide station items are processed. So in a UNIX shell, from the _app_ directory, type in the following loop, on the fly. Let this loop run until it starts reporting that 0 records have been changed:
```
        while (1)
            make port_fill LIMIT=20
```