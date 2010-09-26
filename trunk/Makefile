clean:
	find ./ -name '*~' -exec rm '{}' \; -print -or -name ".*~" -exec rm {} \; -print

clean_for_svn:
	# Cleanup that is not intended for my source area
	find ./ -name '*~' -exec rm '{}' \; -print -or -name ".*~" -exec rm {} \; -print
	find ./ -name 'bulkloader-log*' -exec rm '{}' \;
	find ./ -name '*.pyc' -exec rm '{}' \;

export:
	tar cvf - * | (cd ~/svn/moveable-weather; tar xvf -)
	cp app/my_globals.py.template ~/svn/moveable-weather/app/my_globals.py


