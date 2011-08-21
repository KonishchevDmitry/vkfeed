"""Various utility functions."""

import os

from google.appengine.ext.webapp import template


def render_template(name, params):
    """Renders the specified template."""

    return template.render(os.path.join("../templates", name), params)

