'''Various utility functions.'''

import cgi
import httplib
import logging
import os

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
        page = urlfetch.fetch(url, headers = { 'Accept-Language': 'ru,en' })
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


def render_template(name, params = {}):
    '''Renders the specified template.'''

    return template.render(os.path.join('templates', name), params)

