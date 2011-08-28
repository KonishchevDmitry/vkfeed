# -*- coding: utf-8 -*-

'''Generates the main page.'''

import re
from google.appengine.ext import webapp

import vkfeed.util


class MainPage(webapp.RequestHandler):
    '''Generates the main page.'''


    def get(self):
        '''Processes the GET request.'''

        self.response.out.write(vkfeed.util.render_template('main.html'))


    def post(self):
        '''Processes the POST request.'''

        profile_url = self.request.get('profile_url')

# TODO
        match = re.match(r'''^
            \s*
            (?:https?://(?:vk\.com|vkontakte\.ru)/)?
            (?P<profile_id>[a-zA-Z0-9_-]{5,})/?
            \s*
        $''', profile_url, re.IGNORECASE | re.VERBOSE)

#TODO
        if match:
            self.redirect('/feed/' + match.group('profile_id') + '/wall')
        else:
            self.response.out.write(vkfeed.util.render_template('main.html', {
                'post_error': u'''
                    Неверно указан URL профиля.
                    Адрес должен быть вида http://vkontakte.ru/имя_профиля.
                '''
            }))

