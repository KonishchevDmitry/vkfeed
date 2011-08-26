'''The application's main module.'''

from google.appengine.ext.webapp import WSGIApplication
from google.appengine.ext.webapp.util import run_wsgi_app

from vkfeed.pages.main import MainPage
from vkfeed.pages.not_found import NotFoundPage
from vkfeed.pages.wall import WallPage


def main():
    '''The application's main entry point.'''

    run_wsgi_app(WSGIApplication(
        [
            # TODO: test slashes
            ( '/wall/(.*)', WallPage ),
            ( '/', MainPage ),
            ( '/.*', NotFoundPage ),
        ],
        # TODO
        debug = True
    ))


if __name__ == '__main__':
    main()

