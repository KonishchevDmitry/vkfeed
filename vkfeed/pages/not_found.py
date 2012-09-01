# -*- coding: utf-8 -*-

'''Generates "404 - Page Not Found" page.'''

from __future__ import unicode_literals

import httplib

import webapp2

import vkfeed.utils


class NotFoundPage(webapp2.RequestHandler):
    '''Generates "404 - Page Not Found" page.'''

    def get(self):
        '''Processes the request.'''

        self.error(httplib.NOT_FOUND)
        self.response.headers[b'Content-Type'] = b'text/html; charset=utf-8'
        self.response.out.write(vkfeed.utils.render_template('error.html', {
            'error': '''
                <p>Страница не найдена.</p>

                <p>Возможно:</p>
                <ul>
                    <li>Вы ошиблись при наборе адреса;</li>
                    <li>Вы нашли эту страницу с помощью поисковой системы, но ее больше не существует;</li>
                    <li>Вы прошли по недействительной ссылке на сайте.</li>
                </ul>

                <p>
                    Пожалуйста, перейдите на <a href="/">главную страницу</a> и
                    попытайтесь найти интересующую вас информацию там.
                </p>
            ''',
        }))

