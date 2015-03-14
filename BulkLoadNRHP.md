# Introduction #

The task here is bulkload the handful of csv files comprising the current dataset for the National Registry of Historic Places (NRHP).

The techniques we will use are essentially the same as what we use when [[tide station data](uploading.md) [BulkLoadTideStations](BulkLoadTideStations.md)] for the Moveable Tides app.
In this case, the CSV files we will be loading are:

  * midwest\_doctored.csv
  * northeast\_doctored.csv
  * south1\_doctored.csv
  * south2\_doctored.csv
  * west\_doctored.csv

Uploading the CSV files is simple, and is all controlled from the Makefile in the app directory. The next task is to get the data loaded in a geohash, and this is a bit trickier. As was the case for tides, and weather, we perform this step by running a loop, in the shell:

# Details #

Here are the steps to use bulk upload to upload the NRHP data.

  1. From the  `app` directory, issue the commands:
```
	make upload_northeast_nrhp
	make upload_midwest_nrhp
	make upload_west_nrhp
	make upload_south2_nrhp
	make upload_south1_nrhp
```

  1. Next, we need to make sure the `upload_location` method gets called on each of our newly minted NRHP objects. What we want to do is loop through all the items in the NRHP data store, but doing so in one go will cause App Engine to time out. So the solution we adopt here is to invoke a custom GET method that will update the NRHP locations in batches, and set it up so that it is careful to save its place at the end of each call. Fortunately, App Engine supports _cursors_ for just this purpose.
  1. All that remains is to invoke this GET method, repeatedly, until all NRHP items are processed. So in a UNIX shell, from the _app_ directory, type in the following loop, on the fly. Let this loop run until it starts reporting that 0 records have been changed:
```
        while (1)
            make nrhp_fill LIMIT=1000 CURSOR_NAME=my_nrhp_cursor
```