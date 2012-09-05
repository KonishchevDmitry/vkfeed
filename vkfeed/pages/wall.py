# -*- coding: utf-8 -*-

'''Generates an RSS feed with wall posts.'''

from __future__ import unicode_literals

import cgi
import datetime
import httplib
import logging
import time

import webapp2

from PyRSS2Gen import PyRSS2Gen

from vkfeed import constants
from vkfeed.core import Error
import vkfeed.utils

LOG = logging.getLogger(__name__)


class WallPage(webapp2.RequestHandler):
    '''Generates an RSS feed.'''


    def get(self, profile_name):
        '''Processes the request.

        We don't use VKontakte API because it requires authorization and gives
        tokens with expiration time which is not suitable for RSS generator.
        '''

        user_error = None
        http_status = httplib.OK
        unknown_user_error = False

        try:
            show_photo = ( self.request.get('show_photo', '1') != '0' )
            foreign_posts = ( self.request.get('foreign_posts', '0') != '0' )
            hash_tag_title = ( self.request.get('hash_tag_title', '0') != '0' )
            text_title = ( self.request.get('text_title', '0') != '0' )

            LOG.info('Requested feed for "%s" (foreign_posts = %s, show_photo = %s, hash_tag_title = %s, text_title = %s).',
                profile_name, foreign_posts, show_photo, hash_tag_title, text_title)

            use_api = True
            if_modified_since = None

            if use_api:
                # Use VKontakte API

                from vkfeed.tools import wall_reader

                cur_time = int(time.time())
                headers = self.__get_headers()
                latency = constants.MINUTE_SECONDS
                min_timestamp = cur_time - constants.WEEK_SECONDS

                ## This confuses Google Reader users because it always requests
                ## feeds with 'Cache-Control: max-age=3600' when adding
                ## subscriptions and users often gen an empty feed.
                #for cache_control in headers.get('cache-control', '').split(','):
                #    cache_control = cache_control.strip()
                #    if cache_control.startswith('max-age='):
                #        LOG.info('Applying Cache-Control: %s...', cache_control)
                #        try:
                #            cache_max_age = int(cache_control[len('max-age='):])
                #        except ValueError:
                #            LOG.error('Invalid header: Cache-Control = %s.', cache_control)
                #        else:
                #            if cache_max_age:
                #                min_timestamp = max(min_timestamp, cur_time - cache_max_age - latency)

                if 'if-modified-since' in headers and headers['if-modified-since'] != '0':
                    LOG.info('Applying If-Modified-Since: %s...', headers['if-modified-since'])
                    try:
                        if_modified_since = vkfeed.utils.http_timestamp(headers['if-modified-since'])
                    except Exception as e:
                        LOG.error('Invalid header: If-Modified-Since = %s.', headers['if-modified-since'])
                    else:
                        min_timestamp = max(min_timestamp, if_modified_since - latency)

                max_age = cur_time - min_timestamp
                if max_age > constants.DAY_SECONDS:
                    max_posts_num = 10
                else:
                    max_posts_num = 50

                if 'user-agent' in headers and vkfeed.utils.zero_subscribers(headers['user-agent']):
                    max_posts_num /= 2

                LOG.info('Applying the following limits: max_age=%s, max_posts_num=%s', max_age, max_posts_num)

                try:
                    data = wall_reader.read(profile_name,
                        min_timestamp, max_posts_num, foreign_posts, show_photo, hash_tag_title, text_title)
                except wall_reader.ConnectionError as e:
                    http_status = httplib.BAD_GATEWAY
                    user_error = 'Ошибка соединения с сервером <a href="{0}" target="_blank">{0}</a>.'.format(constants.API_URL)
                    raise
                except wall_reader.ServerError as e:
                    http_status = httplib.NOT_FOUND
                    user_error = unicode(e)
                    raise
            else:
                # Parse HTML from site

                from vkfeed.tools.wall_parser import WallPageParser, ParseError, PrivateGroupError, ProfileNotAvailableError, ServerError

                url = constants.VK_URL + cgi.escape(profile_name)
                url_html = '<a href="{0}" target="_blank">{0}</a>'.format(url)

                if profile_name == 'feed':
                    http_status = httplib.NOT_FOUND
                    user_error = 'Страница {0} не является профилем пользователя или группы.'.format(url_html)
                    raise Error('Unsupported page.')

                try:
                    profile_page = vkfeed.utils.fetch_url(url)
                except vkfeed.utils.HTTPNotFoundError:
                    http_status = httplib.NOT_FOUND
                    user_error = 'Пользователя или группы {0} не существует.'.format(url_html)
                    raise
                except Error:
                    http_status = httplib.BAD_GATEWAY
                    user_error = 'Не удалось загрузить страницу {0}.'.format(url_html)
                    unknown_user_error = True
                    raise

                try:
                    data = WallPageParser().parse(profile_page)
                except PrivateGroupError as e:
                    http_status = httplib.NOT_FOUND
                    user_error = 'Группа {0} является закрытой группой.'.format(url_html)
                    raise
                except ProfileNotAvailableError as e:
                    http_status = httplib.NOT_FOUND
                    user_error = 'Страница пользователя {0} удалена или доступна только авторизованным пользователям.'.format(url_html)
                    raise
                except ServerError as e:
                    LOG.debug('Page contents:\n%s', profile_page)
                    http_status = httplib.BAD_GATEWAY
                    user_error = 'Сервер {0} вернул ошибку{1}'.format(url_html, ':<br />' + e.server_error if e.server_error else '.')
                    unknown_user_error = True
                    raise
                except ParseError as e:
                    LOG.debug('Page contents:\n%s', profile_page)
                    http_status = httplib.NOT_FOUND
                    user_error = 'Сервер вернул страницу, на которой не удалось найти стену с сообщениями пользователя.'
                    unknown_user_error = True
                    raise

                data['url'] = url
                if 'user_photo' not in data:
                    data['user_photo'] = constants.APP_URL + 'images/vk-rss-logo.png'

            LOG.info('Return %s items.', len(data['posts']))

            if if_modified_since is not None and not data['posts']:
                http_status = httplib.NOT_MODIFIED
            else:
                feed = self.__generate_feed(data)
        except Exception as e:
            if isinstance(e, Error):
                if user_error and not unknown_user_error:
                    log_function = LOG.warning
                else:
                    log_function = LOG.error
            else:
                log_function = LOG.exception

            log_function('Unable to generate a feed for "%s": %s', profile_name, e)

            if user_error:
                self.error(http_status)
                error = '<p>Ошибка при генерации RSS-ленты:</p><p>{0}</p>'.format(user_error)
                if unknown_user_error:
                    error += '''<p>
                        Пожалуйста, убедитесь, что вы правильно указали профиль
                        пользователя или группы, и что данный профиль является
                        общедоступным. Если все указано верно, и ошибка
                        повторяется, пожалуйста, свяжитесь с <a
                        href="mailto:{0}">администратором</a>.
                    </p>'''.format(cgi.escape(constants.ADMIN_EMAIL, quote = True))
            else:
                self.error(httplib.INTERNAL_SERVER_ERROR)
                error = '''
                    При генерации RSS-ленты произошла внутренняя ошибка сервера.
                    Если ошибка повторяется, пожалуйста, свяжитесь с <a href="mailto:{0}">администратором</a>.
                '''.format(cgi.escape(constants.ADMIN_EMAIL, quote = True))

            self.response.headers[b'Content-Type'] = b'text/html; charset=utf-8'
            self.response.out.write(vkfeed.utils.render_template('error.html', { 'error': error }))
        else:
            if http_status == httplib.OK:
                self.response.headers[b'Content-Type'] = b'application/rss+xml'
                self.response.out.write(feed)
            else:
                self.error(http_status)


    def __generate_feed(self, data):
        '''Generates a feed from a parsed data.'''

        rss = PyRSS2Gen.RSS2(
            title = data['user_name'],
            link = data['url'],
            description = 'Сообщения со стены пользователя ' + data['user_name'],

            image = PyRSS2Gen.Image(
                url = data['user_photo'],
                title = data['user_name'],
                link = data['url'],
                description = 'Сообщения со стены пользователя ' + data['user_name']
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


    def __get_headers(self):
        '''Returns lowercased headers.'''

        return { name.lower(): value for name, value in self.request.headers.iteritems() }
