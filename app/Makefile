APP=moveable-weather
upload:
	appcfg.py upload_data --config_file=bulkloader.yaml --filename=zipcode.csv --kind=ZipCode .

upload_test:
	appcfg.py upload_data --config_file=bulkloader.yaml --filename=short.csv --kind=ZipCode .


console:
	../tools/console ${APP}.appspot.com

fill:
	curl -X GET 'http://${APP}.appspot.com/locations_update?limit=${LIMIT}&cursor_name=${CURSOR_NAME}'

# make fill LIMIT=200 CURSOR_NAME=my_cursor


run:
	../tools/gae run .
