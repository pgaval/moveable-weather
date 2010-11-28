APP=moveable-weather
upload:
	appcfg.py upload_data --config_file=bulkloader.yaml --filename=zipcode.csv --kind=ZipCode .

upload_ports:
	appcfg.py upload_data --config_file=bulkloader.yaml --filename=better.csv --kind=Port .

upload_ports_test:
	appcfg.py upload_data --config_file=bulkloader.yaml --filename=other.csv --kind=Port .

upload_northeast_nrhp:
	appcfg.py upload_data --config_file=bulkloader.yaml --filename=northeast_doctored.csv --kind=NRHP .

upload_midwest_nrhp:
	appcfg.py upload_data --config_file=bulkloader.yaml --filename=midwest_doctored.csv --kind=NRHP .
# got this far
upload_west_nrhp:
	appcfg.py upload_data --config_file=bulkloader.yaml --filename=west_doctored.csv --kind=NRHP .

upload_south2_nrhp:
	appcfg.py upload_data --config_file=bulkloader.yaml --filename=south2_doctored.csv --kind=NRHP .

upload_south1_nrhp:
	appcfg.py upload_data --config_file=bulkloader.yaml --filename=south1_doctored.csv --kind=NRHP .




upload_northeast_small:
	appcfg.py upload_data --config_file=bulkloader.yaml --filename=small_doctored.csv --kind=NRHP .



upload_test:
	appcfg.py upload_data --config_file=bulkloader.yaml --filename=short.csv --kind=ZipCode .



console:
	../tools/console ${APP}.appspot.com

fill:
	curl -X GET 'http://${APP}.appspot.com/locations_update?limit=${LIMIT}&cursor_name=${CURSOR_NAME}'

# Have to put ports in a geohash
port_fill:
	curl -X GET 'http://2.latest.${APP}.appspot.com/port_locations_update?limit=${LIMIT}&cursor_name=${CURSOR_NAME}'

nrhp_fill:
#	curl -X GET 'http://4.latest.${APP}.appspot.com/nrhp_locations_update?limit=${LIMIT}&cursor_name=${CURSOR_NAME}'
	curl -X GET 'http://${APP}.appspot.com/nrhp_locations_update?limit=${LIMIT}&cursor_name=${CURSOR_NAME}'

nrhp_check:
#	curl -X GET 'http://4.latest.${APP}.appspot.com/nrhp_locations_update?limit=${LIMIT}&cursor_name=${CURSOR_NAME}'
	curl -X GET 'http://${APP}.appspot.com/nrhp_locations_check?limit=${LIMIT}&cursor_name=${CURSOR_NAME}'

# make fill LIMIT=200 CURSOR_NAME=my_cursor
# make port_fill LIMIT=20 CURSOR_NAME=my_port_cursor
# make nrhp_fill LIMIT=1000 CURSOR_NAME=my_nrhp_cursor
# make nrhp_check LIMIT=1000 CURSOR_NAME=my_nrhp_checker_cursor

# Because some ports don't have tide data
clean_ports:
	curl -X GET 'http://${APP}.appspot.com/clean_ports?limit=${LIMIT}&cursor_name=${CURSOR_NAME}'

# make clean_ports LIMIT=20 CURSOR_NAME=my_port_cleaner_cursor3

run:
	../tools/gae run .

ship_to_moveable_weather:
	tar cvf - config.py main.py member.py model.py tides.py weather.py better.csv Makefile bulkloader.yaml| ( cd ../../moveable-weather/app; tar xvf -)
