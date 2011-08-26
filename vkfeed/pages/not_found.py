# -*- coding: utf-8 -*-

'''Generates "404 - Page Not Found" page.'''

import httplib

from google.appengine.ext import webapp

import vkfeed.util


class NotFoundPage(webapp.RequestHandler):
    '''Generates "404 - Page Not Found" page.'''

    def get(self):
        '''Processes the request.'''

        self.error(httplib.NOT_FOUND)
        self.response.out.write(vkfeed.util.render_template('error.html', {
            'error': u'''
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

