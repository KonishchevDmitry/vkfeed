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
# TODO: quotes


class WallPage(webapp.RequestHandler):
    '''Generates an RSS feed.'''


    def get(self, profile_name):
        '''Processes the request.'''

        user_error = None

# TODO: check profile_name
        try:
            logging.info('Requested feed for "%s".', profile_name)

            url = constants.VK_URL + profile_name

            try:
                profile_page = vkfeed.util.fetch_url(url)
            except Error:
                # TODO: more descriptive
                user_error = u'Не удалось загрузить страницу <a href="%s" target="_blank">%s</a>.' % (url, url)
                raise

            try:
            # TODO: why not API
                data = WallPageParser().parse(profile_page)
            except ParseError, e:
                user_error = (
                    u'Сервер вернул страницу, на которой не удалось найти стену с сообщениями пользователя. '
                    u'Пожалуйста, убедитесь, что вы правильно указали профиль пользователя/группы. '
                    u'Если все указано верно, и ошибка повторяется, пожалуйста, свяжитесь с <a href="mailto:%s">администратором</a>.'
                    % (cgi.escape(constants.ADMIN_EMAIL, quote = True))
                )
                raise

            data['url'] = url
            # TODO
            #match = re.search(r'''<div id="public_avatar.+?<img src="([^"]+)"''', profile_page, re.DOTALL)
            if 'user_photo' not in data:
                data['user_photo'] = constants.APP_URL + 'images/vk-rss-logo.png'
            feed = self.__generate_feed(data)
        except Exception, e:
            # TODO
            if isinstance(e, Error):
                logging.error('Unable to generate a feed for "%s": %s.', url, e)
            else:
                logging.exception('Unable to generate a feed for "%s": %s.', url, e)

            if user_error:
                self.error(httplib.BAD_GATEWAY)
                error = u'Ошибка при генерации RSS-ленты. %s' % (user_error)
            else:
                self.error(httplib.INTERNAL_SERVER_ERROR)
                error = (
                    u'При генерации RSS-ленты произошла внутренняя ошибка сервера. '
                    u'Если ошибка повторяется, пожалуйста, свяжитесь с <a href="mailto:%s">администратором</a>.'
                    % (cgi.escape(constants.ADMIN_EMAIL, quote = True))
                )

            self.response.out.write(vkfeed.util.render_template('error.html', {
            # TODO
                'feed_source': url,
                'error':       error,
            }))
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

