# Using Bulk Loader #

Google's App Engine offers a powerful set of tools for bulk loading data. We use it in Moveable Weather for uploading a [freely-available CSV file](http://www.boutell.com/zipcodes/) containing locational information about all U.S. zip codes.


# Details #

There is great power in the bulk upload facility, and along with this power, comes complexity. Moveable Weather includes the following components, which you can use, to upload the data:

  * bulkloader.yaml: a configuration file needed by the bulk loader
  * zipcode.csv: comprises a database U.S zip codes, with their cities, states, latitudes and longitudes
  * app/Makefile: contains some useful "make" targets for doing the uploading and configuration