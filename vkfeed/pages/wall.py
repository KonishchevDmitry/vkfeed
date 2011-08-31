#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Generates an RSS feed with wall posts.'''

import cgi
import httplib
import logging
import re

from google.appengine.ext import webapp

from PyRSS2Gen import PyRSS2Gen

from vkfeed import constants
from vkfeed.core import Error
import vkfeed.util
from vkfeed.tools.wall_parser import WallPageParser, ParseError

LOG = logging.getLogger(__name__)


class WallPage(webapp.RequestHandler):
    '''Generates an RSS feed.'''


    def get(self, profile_name):
        '''Processes the request.

        We don't use VKontakte API because it requires authorization and gives
        tokens with expiration time which is not suitable for RSS generator.
        '''

        user_error = None

        try:
            LOG.info('Requested feed for "%s".', profile_name)

            url = constants.VK_URL + cgi.escape(profile_name)

            try:
                profile_page = vkfeed.util.fetch_url(url)
            except Error:
                user_error = u'Не удалось загрузить страницу <a href="%s" target="_blank">%s</a>.' % (url, url)
                raise

            try:
                data = WallPageParser().parse(profile_page)
            except ParseError, e:
                user_error = u'Сервер вернул страницу, на которой не удалось найти стену с сообщениями пользователя.'
                raise

            data['url'] = url
            if 'user_photo' not in data:
                data['user_photo'] = constants.APP_URL + 'images/vk-rss-logo.png'

            feed = self.__generate_feed(data)
        except Exception, e:
            (LOG.error if isinstance(e, Error) else LOG.exception)(
                'Unable to generate a feed for "%s": %s.', url, e)

            if user_error:
                self.error(httplib.BAD_GATEWAY)
                error = u'''
                    Ошибка при генерации RSS-ленты. %s
                    Пожалуйста, убедитесь, что вы правильно указали профиль пользователя/группы.
                    Если все указано верно, и ошибка повторяется, пожалуйста, свяжитесь с <a href="mailto:%s">администратором</a>.
                ''' % (user_error, cgi.escape(constants.ADMIN_EMAIL, quote = True))
            else:
                self.error(httplib.INTERNAL_SERVER_ERROR)
                error = u'''
                    При генерации RSS-ленты произошла внутренняя ошибка сервера.
                    Если ошибка повторяется, пожалуйста, свяжитесь с <a href="mailto:%s">администратором</a>.
                ''' % (cgi.escape(constants.ADMIN_EMAIL, quote = True))

            self.response.out.write(vkfeed.util.render_template('error.html', { 'error': error }))
        else:
            self.response.headers['Content-Type'] = 'application/rss+xml'
            self.response.out.write(feed)


    def __generate_feed(self, data):
        '''Generates a feed from a parsed data.'''

        rss = PyRSS2Gen.RSS2(
            title = data['user_name'],
            link = data['url'],
            description = u'Сообщения со стены пользователя %s' % data['user_name'],

            image = PyRSS2Gen.Image(
                url = data['user_photo'],
                title = data['user_name'],
                link = data['url'],
                description = u'Сообщения со стены пользователя %s' % data['user_name']
            ),

            items = [
                PyRSS2Gen.RSSItem(
                  title = data['user_name'],
                  link = post['url'],
                  description = post['text'],
                  guid = PyRSS2Gen.Guid(post['url'])
                ) for post in data['posts']
            ]
        )

        return rss.to_xml('utf-8')

