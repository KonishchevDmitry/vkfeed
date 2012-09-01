'''Various utility functions.'''

from __future__ import unicode_literals

import calendar
import cgi
import datetime
import httplib
import logging
import os
import re

if not os.getenv('VKFEED_TESTS'):
    import google.appengine.api.urlfetch as urlfetch
    from google.appengine.ext.webapp import template

from vkfeed.core import Error

LOG = logging.getLogger(__name__)


class HTTPNotFoundError(Error):
    '''Raised on HTTP Page Not Found error.'''

    def __init__(self, *args, **kwargs):
        Error.__init__(self, *args, **kwargs)


def fetch_url(url, content_type = 'text/html'):
    '''Fetches the specified URL.'''

    LOG.info('Fetching "%s"...', url)

    try:
        page = _fetch_url(url, headers = { 'Accept-Language': 'ru,en' })
    except urlfetch.Error as e:
        raise Error('Failed to fetch the page: {0}.', e)
    else:
        if page.status_code == httplib.OK:
            LOG.info('"%s" has been successfully fetched.', url)
        else:
            error_class = HTTPNotFoundError if page.status_code == httplib.NOT_FOUND else Error
            raise error_class('The server returned error: {0} ({1}).',
                httplib.responses.get(page.status_code, 'Unknown error'), page.status_code)

    content = page.content

    for key in page.headers:
        if key.lower() == 'content-type':
            value, params = cgi.parse_header(page.headers[key])

            if value != content_type:
                raise Error('The server returned a page with invalid content type: {0}.', value)

            if content_type.startswith('text/'):
                for param in params:
                    if param.lower() == 'charset':
                        content_encoding = params[param]
                        break
                else:
                    content_encoding = 'UTF-8'

                try:
                    content = content.decode(content_encoding)
                except UnicodeDecodeError:
                    raise Error('The server returned a page in invalid encoding.')

            break
    else:
        raise Error('The server returned a page with missing content type.')

    return content


def http_timestamp(date):
    """Returns a timestamp corresponding to the specified HTTP date.

    FIXME: there is no support for timezone parsing in standard python
    libraries. Thus, we are supporting a GMT zone only.
    """

    for fmt in (
        "%a, %d %b %Y %H:%M:%S GMT", # RFC 1123
        "%a, %d %b %Y %H:%M:%S GMT+00:00", # RFC 1123
        "%a, %d %b %Y %H:%M:%S +0000", # ???
        "%A, %d-%b-%y %H:%M:%S GMT", # RFC 850
        "%A, %d-%b-%y %H:%M:%S GMT+00:00", # RFC 850
        "%a %b %d %H:%M:%S %Y" # asctime(3)
    ):
        try:
            timeo = datetime.datetime.strptime(date, fmt)
        except ValueError:
            continue

        return calendar.timegm(datetime.datetime.utctimetuple(timeo))

    raise Exception("Invalid HTTP date format")


def render_template(name, params = {}):
    '''Renders the specified template.'''

    return template.render(os.path.join('templates', name), params)


def zero_subscribers(user_agent):
    '''Returns True if the feed has zero subscribers.'''

    return re.search(r'[^0-9]0\s+(?:reader|subscriber)', user_agent, re.IGNORECASE) is not None


def _fetch_url(*args, **kwargs):
    '''
    Sometimes urlfetch.fetch() raises weird error 'ApplicationError: 5' when it
    shouldn't. So this wrapper ignores errors and tries to fetch the URL again.
    '''

    tries = 3

    while True:
        try:
            return urlfetch.fetch(*args, **kwargs)
        except urlfetch.Error as e:
            if tries <= 1:
                raise e
            tries -= 1
