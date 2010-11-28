from google.appengine.ext import webapp
# from math import sin, cos, sqrt, atan2, asin, floor
# from math import *
import math

# For each co-ordinate system we do, what are the A, B and E2 values?
# List is A, B, E^2 (E^2 calculated after)
abe_values = {
	'wgs84': [ 6378137.0, 6356752.3141, -1 ],
	'osgb' : [ 6377563.396, 6356256.91, -1 ],
	'osie' : [ 6377340.189, 6356034.447, -1 ]
}

# The earth's radius, in meters, as taken from an average of the WGS84
#  a and b parameters (should be close enough)
earths_radius = (abe_values['wgs84'][0] + abe_values['wgs84'][1]) / 2.0


class MyGeoUtils (webapp.RequestHandler):

    def approx_ellipsoid_dist (self, (lat1, lon1), (lat2, lon2)):
        """approx_ellipsoid_dist((lat1, lon1), (lat2, lon2)):
        Input: lat1, lon1, lat2, lon2: latitude and longitude (in degrees) of two points on Earth.
        Output: distance in kilometers "crow fly" between the two points.
        If you want less precision use sperical_distance.
        If you want more precision use ellipsoid_distance."""
        # http://www.codeguru.com/Cpp/Cpp/algorithms/article.php/c5115/
        # By Andy McGovern, translated to Python
        DE2RA = 0.01745329252 # Degrees to radians
        ERAD = 6378.137
        FLATTENING = 1.000000 / 298.257223563 # Earth flattening (WGS84)
        EPS = 0.000000000005

        if lon1 == lon2 and lat1 == lat2:
            return 0.0
        lat1 = DE2RA * lat1
        lon1 = -DE2RA * lon1
        lat2 = DE2RA * lat2
        lon2 = -DE2RA * lon2

        F = (lat1 + lat2) / 2.0
        G = (lat1 - lat2) / 2.0
        L = (lon1 - lon2) / 2.0

        sing = sin(G)
        cosl = cos(L)
        cosf = cos(F)
        sinl = sin(L)
        sinf = sin(F)
        cosg = cos(G)

        S = sing*sing*cosl*cosl + cosf*cosf*sinl*sinl
        C = cosg*cosg*cosl*cosl + sinf*sinf*sinl*sinl
        W = atan2(sqrt(S), sqrt(C))
        R = sqrt(S*C) / W
        H1 = (3 * R - 1.0) / (2.0 * C)
        H2 = (3 * R + 1.0) / (2.0 * S)
        D = 2 * W * ERAD
        return D * (1 + FLATTENING * H1 * sinf*sinf*cosg*cosg - FLATTENING*H2*cosf*cosf*sing*sing)

# See http://gagravarr.org/code/ for updates and information
#
# GPL
#
# Nick Burch - v0.06 (30/05/2007)

    def calculate_distance_and_bearing(self, from_lat_dec,from_long_dec,to_lat_dec,to_long_dec):
	"""Uses the spherical law of cosines to calculate the distance and bearing between two positions"""

	# Turn them all into radians
	from_theta = float(from_lat_dec)  / 360.0 * 2.0 * math.pi
	from_landa = float(from_long_dec) / 360.0 * 2.0 * math.pi
	to_theta = float(to_lat_dec)  / 360.0 * 2.0 * math.pi
	to_landa = float(to_long_dec) / 360.0 * 2.0 * math.pi

	d = math.acos(
			math.sin(from_theta) * math.sin(to_theta) +
			math.cos(from_theta) * math.cos(to_theta) * math.cos(to_landa-from_landa)
		) * earths_radius

	bearing = math.atan2(
			math.sin(to_landa-from_landa) * math.cos(to_theta),
			math.cos(from_theta) * math.sin(to_theta) -
			math.sin(from_theta) * math.cos(to_theta) * math.cos(to_landa-from_landa)
		)
	bearing = bearing / 2.0 / math.pi * 360.0

	return [d,bearing]
