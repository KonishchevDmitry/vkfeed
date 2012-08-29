'''The application's main module.'''

from __future__ import unicode_literals

from webapp2 import WSGIApplication

from vkfeed.pages.main import MainPage
from vkfeed.pages.not_found import NotFoundPage
from vkfeed.pages.wall import WallPage


app = WSGIApplication([
    ( '/feed/([^/]+)/wall/?', WallPage ),
    ( '/',                    MainPage ),
    ( '.*',                   NotFoundPage ),
], debug = False)

