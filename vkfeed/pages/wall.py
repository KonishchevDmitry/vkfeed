#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Generates an RSS feed with wall posts.'''

import cgi
import httplib
import logging

from google.appengine.ext import webapp

from PyRSS2Gen import PyRSS2Gen

from vkfeed import constants
from vkfeed.core import Error
import vkfeed.util
from vkfeed.tools.wall_parser import WALL_TYPE_PROFILE_PAGE, WALL_TYPE_WALL_PAGE
from vkfeed.tools.wall_parser import WallPageParser, ParseError, PrivateGroupError, ProfileDeletedError, ServerError

LOG = logging.getLogger(__name__)


class WallPage(webapp.RequestHandler):
    '''Generates an RSS feed.'''


    def get(self, profile_name):
        '''Processes the request.

        We don't use VKontakte API because it requires authorization and gives
        tokens with expiration time which is not suitable for RSS generator.
        '''

        http_status = None
        user_error = None
        unknown_user_error = False

        try:
            LOG.info('Requested feed for "%s".', profile_name)

            url = constants.VK_URL + cgi.escape(profile_name)
            url_html = '<a href="%s" target="_blank">%s</a>' % (url, url)

            try:
                profile_page = vkfeed.util.fetch_url(url)
            except vkfeed.util.HTTPNotFoundError:
                http_status = httplib.NOT_FOUND
                user_error = u'Пользователя или группы %s не существует.' % url_html
                raise
            except Error:
                http_status = httplib.BAD_GATEWAY
                user_error = u'Не удалось загрузить страницу %s.' % url_html
                unknown_user_error = True
                raise

            try:
                if profile_name.startswith("wall-"):
                    wall_type = WALL_TYPE_WALL_PAGE
                else:
                    wall_type = WALL_TYPE_PROFILE_PAGE

                data = WallPageParser().parse(profile_page, wall_type)
            except PrivateGroupError, e:
                http_status = httplib.NOT_FOUND
                user_error = u'Группа %s является закрытой группой.' % url_html
                raise
            except ProfileDeletedError, e:
                http_status = httplib.NOT_FOUND
                user_error = u'Страница пользователя %s удалена.' % url_html
                raise
            except ServerError, e:
                LOG.debug(u'Page contents:\n%s', profile_page)
                http_status = httplib.BAD_GATEWAY
                user_error = u'Сервер %s вернул ошибку%s' % (url_html, ':<br />' + e.server_error if e.server_error else '.')
                unknown_user_error = True
                raise
            except ParseError, e:
                LOG.debug(u'Page contents:\n%s', profile_page)
                http_status = httplib.NOT_FOUND
                user_error = u'Сервер вернул страницу, на которой не удалось найти стену с сообщениями пользователя.'
                unknown_user_error = True
                raise

            data['url'] = url
            if 'user_photo' not in data:
                data['user_photo'] = constants.APP_URL + 'images/vk-rss-logo.png'

            feed = self.__generate_feed(data)
        except Exception, e:
            if isinstance(e, Error):
                if user_error and not unknown_user_error:
                    log_function = LOG.warning
                else:
                    log_function = LOG.error
            else:
                log_function = LOG.exception

            log_function('Unable to generate a feed for "%s": %s', url, e)

            if user_error:
                self.error(http_status)
                error = u'<p>Ошибка при генерации RSS-ленты.</p><p>%s</p>' % user_error
                if unknown_user_error:
                    error += u'''<p>
                        Пожалуйста, убедитесь, что вы правильно указали профиль
                        пользователя или группы, и что данный профиль является
                        общедоступным. Если все указано верно, и ошибка
                        повторяется, пожалуйста, свяжитесь с <a
                        href="mailto:%s">администратором</a>.
                    </p>''' % cgi.escape(constants.ADMIN_EMAIL, quote = True)
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
                  title = post['title'],
                  link = post['url'],
                  description = post['text'],
                  guid = PyRSS2Gen.Guid(post['url'])
                ) for post in data['posts']
            ]
        )

        return rss.to_xml('utf-8')

