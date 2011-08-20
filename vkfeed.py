#from google.appengine.ext import webapp
#from google.appengine.ext.webapp.util import run_wsgi_app
#
#class MainPage(webapp.RequestHandler):
#    def get(self):
#        self.response.headers['Content-Type'] = 'text/plain'
#        self.response.out.write('Hello, webapp World!')
#        help(self)
#        #self.redirect()
#
#application = webapp.WSGIApplication(
#                                     [('/', MainPage)],
#                                     debug=True)
#
#def main():
#    run_wsgi_app(application)
#
#if __name__ == "__main__":
#    main()



import os
from google.appengine.ext.webapp import template
import cgi

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import logging
from google.appengine.api.urlfetch import fetch
class Feed(webapp.RequestHandler):
    def get(self):
        logging.error(">")

class MainPage(webapp.RequestHandler):
    def get(self):
        #guestbook_name=self.request.get('guestbook_name')
        #greetings_query = Greeting.all().ancestor(
        #    guestbook_key(guestbook_name)).order('-date')
        #greetings = greetings_query.fetch(10)

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        template_values = {
            'greetings': "ggg",
            'url': url,
            'url_linktext': url_linktext,
        }

        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, template_values))

class Guestbook(webapp.RequestHandler):
    def post(self):
        self.response.out.write('<html><body>You wrote:<pre>')
        self.response.out.write(cgi.escape(self.request.get('content')))
        self.response.out.write('</pre></body></html>')

application = webapp.WSGIApplication(
                                     [('/', MainPage),
                                      ("/feed", Feed),
                                      ('/sign', Guestbook)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
