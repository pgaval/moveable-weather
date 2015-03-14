# Introduction #

The zipcode.csv file, [freely available](http://www.boutell.com/zipcodes/), has been altered slightly, for use with Moveable Weather. An extra field, called `has_location` has been added to the end of each line. Initially, the value of this field is set to `0` for each line. After you upload the `zipcode.csv` file, you will need to loop through each record in this data, calling a special method called `update_location`. The purpose of this method, inherited from the `GeoName` class, is to ensure that each latitude/longitude pair is stored in a _geohash_. This will enable _proximity searches_, which are critical.

The reason proximity searches are necessary is that each zip code in the database is associated with a partilar latitude/longitude pair which we can thing of as occupying the center of the particular zip code. But data about a user's location, coming in via Google Latitude, will be arbitrary, and thus, we'll need to be able to compute which zip code's "neighborhood" it falls within. This is what a proximity search is.

# Details #

Here are the steps to use bulk upload to upload the zip code data. This will cause all your zip code today to be uploaded, and may take an hour or so.

  1. From the  `app` directory, issue the command:
```
     make upload
```
  1. Next, we need to make sure the `upload_location` method gets called on each of our newly minted ZipCode objects. What we want to do is loop through all the items in the ZipCode data store, but doing so in one go will cause App Engine to time out. So the solution we adopt here is to invoke a custom GET method that will update the zip codes in batches, and set it up so that it is careful to save its place at the end of each call. Fortunately, App Engine supports _cursors_ for just this purpose.
  1. All that remains is to invoke this GET method, repeatedly, until all zip code items are processed. So in a UNIX shell, from the _app_ directory, type in the following loop, on the fly. Let this loop run until it starts reporting that 0 records have been changed:
```
        while (1)
            make fill LIMIT=100
```