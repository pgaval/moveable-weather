from BeautifulSoup import BeautifulSoup
from google.appengine.api import urlfetch

search_url = 'http://en.wikipedia.org/w/index.php?title=Special:Search&search=refnum+79000205'
resp = urlfetch.fetch(search_url)
resp.status_code
contents = resp.content
soup = BeautifulSoup(contents)
results = soup.find("ul", {"class" : "mw-search-results"})

new_search_url = 'http://en.wikipedia.org/wiki/Rundlet-May_House'
