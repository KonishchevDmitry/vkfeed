"""Various utility functions."""

import cgi
import httplib
import logging
import os

import google.appengine.api.urlfetch as urlfetch
from google.appengine.ext.webapp import template


def fetch_url(url):
    """Fetches the specified URL."""

    logging.info("Fetching '%s'...", url)

    try:
        page = urlfetch.fetch(url)
    except urlfetch.Error, e:
        raise Error("Failed to fetch the page: %s.", e)
    else:
        if page.status_code == httplib.OK:
            logging.info("'%s' has been successfully fetched.", url)
        else:
            raise Error("The server returned error: %s (%s).",
                httplib.responses.get(page.status_code, "Unknown error"), page.status_code)

    content_encoding = "UTF-8"

    for key in page.headers:
        if key.lower() == "content-type":
            content_type, content_type_params = cgi.parse_header(page.headers[key])

            if content_type != "text/html":
                raise Error("The server returned a page with invalid content type: %s", content_type)

            for param in content_type_params:
                if param.lower() == "charset":
                    content_encoding = content_type_params[param]

            break
    else:
        raise Error("The server returned a page with missing content type.")

    try:
        return page.content.decode(content_encoding)
    except UnicodeDecodeError:
        raise Error("The server returned a page in invalid encoding.")


def render_template(name, params):
    """Renders the specified template."""

    return template.render(os.path.join("../templates", name), params)

