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
from vkfeed.wall_parser import WallPageParser, ParseError
# TODO: quotes


class WallPage(webapp.RequestHandler):
    '''Generates an RSS feed.'''


    def get(self, profile_name):
        '''Processes the request.'''

        user_error = None

# TODO: check profile_name
        try:
            logging.info('Requested feed for "%s".', profile_name)

            url = 'http://vk.com/' + profile_name

            try:
                profile_page = vkfeed.util.fetch_url(url)
            except Error:
                user_error = u'Не удалось загрузить страницу <a href="%s" target="_blank">%s</a>.' % (url, url)
                raise

            try:
                data = WallPageParser().parse(profile_page)
            except ParseError, e:
                user_error = (
                    u'Сервер вернул страницу, на которой не удалось найти стену с сообщениями пользователя. '
                    u'Пожалуйста, убедитесь, что вы правильно указали профиль пользователя/группы. '
                    u'Если все указано верно, и ошибка повторяется, пожалуйста, свяжитесь с <a href="mailto:%s">администратором</a>.'
                    % (cgi.escape(constants.admin_email, quote = True))
                )
                raise

            data['url'] = url
            # TODO
            match = re.search(r'''<div id="public_avatar.+?<img src="([^"]+)"''', profile_page, re.DOTALL)
            data['image'] = match.group(1)
            feed = self.__generate_feed(data)
        except Exception, e:
            logging.error('Unable to generate a feed for "%s": %s.', url, e)

            if user_error:
                self.error(httplib.BAD_GATEWAY)
                error = u'Ошибка при генерации RSS-ленты. %s' % (user_error),
            else:
                self.error(httplib.INTERNAL_SERVER_ERROR)
                error = (
                    u'При генерации RSS-ленты произошла внутренняя ошибка сервера. '
                    u'Если ошибка повторяется, пожалуйста, свяжитесь с <a href="mailto:%s">администратором</a>.'
                    % (cgi.escape(constants.admin_email, quote = True))
                )

            self.response.out.write(vkfeed.util.render_template('feed_error.html', {
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
                # TODO
                url = data['image'],
                title = data['user_name'],
                link = data['url'],
                width = None, # def: 88, max 144
                height = None, # def: 31, max 400
                description = u'Сообщения со стены пользователя %s' % data['user_name']
            ),

            items = [
                PyRSS2Gen.RSSItem(
                  title = data['user_name'],
                  # TODO
                  link = 'http://no-url.com/',
                  description = post['text'],
                  # TODO
                  guid = PyRSS2Gen.Guid('http://' + post['id'])
                ) for post in data['posts']
            ]
        )

        return rss.to_xml('utf-8')

