#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Generates an RSS feed with wall posts.'''

import cgi
import datetime
import httplib
import logging
import urllib

import webapp2

from PyRSS2Gen import PyRSS2Gen

from vkfeed import constants
from vkfeed.core import Error
import vkfeed.util

LOG = logging.getLogger(__name__)


class WallPage(webapp2.RequestHandler):
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
            show_photo = ( self.request.get('show_photo', '1') != '0' )
            foreign_posts = ( self.request.get('foreign_posts', '0') != '0' )
            hash_tag_title = ( self.request.get('hash_tag_title', '0') != '0' )
            text_title = ( self.request.get('text_title', '0') != '0' )

            LOG.info(u'Requested feed for "%s" (foreign_posts = %s, show_photo = %s, hash_tag_title = %s, text_title = %s).',
                profile_name, foreign_posts, show_photo, hash_tag_title, text_title)

            use_api = True

            if use_api:
                # Use VKontakte API

                from vkfeed.tools import wall_reader

                try:
                    data = wall_reader.read(profile_name, foreign_posts, show_photo, hash_tag_title, text_title)
                except wall_reader.ConnectionError as e:
                    http_status = httplib.BAD_GATEWAY
                    user_error = u'Ошибка соединения с сервером <a href="{0}" target="_blank">{0}</a>.'.format(constants.API_URL)
                    raise
                except wall_reader.ServerError as e:
                    http_status = httplib.NOT_FOUND
                    user_error = unicode(e)
                    raise
            else:
                # Parse HTML from site

                from vkfeed.tools.wall_parser import WallPageParser, ParseError, PrivateGroupError, ProfileNotAvailableError, ServerError

                url = constants.VK_URL + cgi.escape(profile_name)
                url_html = u'<a href="{0}" target="_blank">{0}</a>'.format(url)

                if profile_name == 'feed':
                    http_status = httplib.NOT_FOUND
                    user_error = u'Страница {0} не является профилем пользователя или группы.'.format(url_html)
                    raise Error('Unsupported page.')

                try:
                    profile_page = vkfeed.util.fetch_url(url)
                except vkfeed.util.HTTPNotFoundError:
                    http_status = httplib.NOT_FOUND
                    user_error = u'Пользователя или группы {0} не существует.'.format(url_html)
                    raise
                except Error:
                    http_status = httplib.BAD_GATEWAY
                    user_error = u'Не удалось загрузить страницу {0}.'.format(url_html)
                    unknown_user_error = True
                    raise

                try:
                    data = WallPageParser().parse(profile_page)
                except PrivateGroupError as e:
                    http_status = httplib.NOT_FOUND
                    user_error = u'Группа {0} является закрытой группой.'.format(url_html)
                    raise
                except ProfileNotAvailableError as e:
                    http_status = httplib.NOT_FOUND
                    user_error = u'Страница пользователя {0} удалена или доступна только авторизованным пользователям.'.format(url_html)
                    raise
                except ServerError as e:
                    LOG.debug(u'Page contents:\n%s', profile_page)
                    http_status = httplib.BAD_GATEWAY
                    user_error = u'Сервер {0} вернул ошибку{1}'.format(url_html, ':<br />' + e.server_error if e.server_error else '.')
                    unknown_user_error = True
                    raise
                except ParseError as e:
                    LOG.debug(u'Page contents:\n%s', profile_page)
                    http_status = httplib.NOT_FOUND
                    user_error = u'Сервер вернул страницу, на которой не удалось найти стену с сообщениями пользователя.'
                    unknown_user_error = True
                    raise

                data['url'] = url
                if 'user_photo' not in data:
                    data['user_photo'] = constants.APP_URL + 'images/vk-rss-logo.png'

            feed = self.__generate_feed(data)
        except Exception as e:
            if isinstance(e, Error):
                if user_error and not unknown_user_error:
                    log_function = LOG.warning
                else:
                    log_function = LOG.error
            else:
                log_function = LOG.exception

            log_function(u'Unable to generate a feed for "%s": %s', profile_name, e)

            if user_error:
                self.error(http_status)
                error = u'<p>Ошибка при генерации RSS-ленты:</p><p>{0}</p>'.format(user_error)
                if unknown_user_error:
                    error += u'''<p>
                        Пожалуйста, убедитесь, что вы правильно указали профиль
                        пользователя или группы, и что данный профиль является
                        общедоступным. Если все указано верно, и ошибка
                        повторяется, пожалуйста, свяжитесь с <a
                        href="mailto:{0}">администратором</a>.
                    </p>'''.format(cgi.escape(constants.ADMIN_EMAIL, quote = True))
            else:
                self.error(httplib.INTERNAL_SERVER_ERROR)
                error = u'''
                    При генерации RSS-ленты произошла внутренняя ошибка сервера.
                    Если ошибка повторяется, пожалуйста, свяжитесь с <a href="mailto:{0}">администратором</a>.
                '''.format(cgi.escape(constants.ADMIN_EMAIL, quote = True))

            self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
            self.response.out.write(vkfeed.util.render_template('error.html', { 'error': error }))
        else:
            self.response.headers['Content-Type'] = 'application/rss+xml'
            self.response.out.write(feed)


    def __generate_feed(self, data):
        '''Generates a feed from a parsed data.'''

        rss = PyRSS2Gen.RSS2(
            title = data['user_name'],
            link = data['url'],
            description = u'Сообщения со стены пользователя ' + data['user_name'],

            image = PyRSS2Gen.Image(
                url = data['user_photo'],
                title = data['user_name'],
                link = data['url'],
                description = u'Сообщения со стены пользователя ' + data['user_name']
            ),

            items = [
                PyRSS2Gen.RSSItem(
                  title = post['title'],
                  link = post['url'],
                  description = post['text'],
                  guid = PyRSS2Gen.Guid(post['url']),
                  pubDate = post.get('date', datetime.datetime.utcnow())
                ) for post in data['posts']
            ]
        )

        return rss.to_xml('utf-8')

