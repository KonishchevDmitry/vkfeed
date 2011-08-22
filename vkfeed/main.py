"""The application's main module."""

from google.appengine.ext.webapp import WSGIApplication
from google.appengine.ext.webapp.util import run_wsgi_app

from vkfeed.feed import Feed


def main():
    """The application's main entry point."""

    run_wsgi_app(WSGIApplication(
        [
            ( "/wall/(.*)", Feed ),
        ],
        # TODO
        debug = True
    ))


if __name__ == "__main__":
    main()

