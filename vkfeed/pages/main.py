# -*- coding: utf-8 -*-

'''Generates the main page.'''

from __future__ import unicode_literals

import re
import urllib

import webapp2

import vkfeed.utils


class MainPage(webapp2.RequestHandler):
    '''Generates the main page.'''


    def get(self):
        '''Processes a GET request.'''

        self.response.headers[b'Content-Type'] = b'text/html; charset=utf-8'
        self.response.out.write(vkfeed.utils.render_template('main.html'))


    def post(self):
        '''Processes a POST request.'''

        profile_url = self.request.get('profile_url', '')

        match = re.match(r'''^
            \s*
            (?:https?://(?:www\.)?(?:vk\.com|vkontakte\.ru)/)?
            (?P<profile_id>[a-zA-Z0-9._-]+)/?
            \s*
        $''', profile_url, re.IGNORECASE | re.VERBOSE)

        if match:
            params = {}

            if self.request.get('foreign_posts') == '1':
                params['foreign_posts'] = '1'

            if self.request.get('big_photos') == '1':
                params['big_photos'] = '1'

            if self.request.get('show_photo') != '1':
                params['show_photo'] = '0'

            params = '?' + urllib.urlencode(params) if params else ''

            self.redirect('/feed/' + match.group('profile_id') + '/wall' + params)
        else:
            self.response.headers[b'Content-Type'] = b'text/html; charset=utf-8'
            self.response.out.write(vkfeed.utils.render_template('main.html', {
                'post_error': '''
                    Неверно указан URL профиля.
                    Адрес должен быть вида http://vk.com/имя_профиля.
                    Имя профиля должно удовлетворять требованиям, предъявляемым администрацией ВКонтакте.
                '''
            }))
