APP=moveable-weather
upload:
	appcfg.py upload_data --config_file=bulkloader.yaml --filename=zipcode.csv --kind=ZipCode .

upload_ports:
	appcfg.py upload_data --config_file=bulkloader.yaml --filename=better.csv --kind=Port .

upload_ports_test:
	appcfg.py upload_data --config_file=bulkloader.yaml --filename=other.csv --kind=Port .

upload_test:
	appcfg.py upload_data --config_file=bulkloader.yaml --filename=short.csv --kind=ZipCode .



console:
	../tools/console ${APP}.appspot.com

fill:
	curl -X GET 'http://${APP}.appspot.com/locations_update?limit=${LIMIT}&cursor_name=${CURSOR_NAME}'

# Have to put ports in a geohash
port_fill:
	curl -X GET 'http://2.latest.${APP}.appspot.com/port_locations_update?limit=${LIMIT}&cursor_name=${CURSOR_NAME}'

# make fill LIMIT=200 CURSOR_NAME=my_cursor
# make port_fill LIMIT=20 CURSOR_NAME=my_port_cursor

# Because some ports don't have tide data
clean_ports:
	curl -X GET 'http://2.latest.${APP}.appspot.com/clean_ports?limit=${LIMIT}&cursor_name=${CURSOR_NAME}'

# make clean_ports LIMIT=20 CURSOR_NAME=my_port_cleaner_cursor3

run:
	../tools/gae run .

ship_to_moveable_weather:
	tar cvf - config.py main.py member.py model.py tides.py weather.py better.csv Makefile bulkloader.yaml| ( cd ../../moveable-weather/app; tar xvf -)
