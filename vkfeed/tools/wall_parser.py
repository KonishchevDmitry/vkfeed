# -*- coding: utf-8 -*-

'''Parses VKontakte wall pages.'''

from __future__ import unicode_literals

import cgi
import datetime
import logging
import re
import urllib

from vkfeed import constants
from vkfeed.core import Error
from vkfeed.tools.html_parser import HTMLPageParser

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)


class ParseError(Error):
    '''Raised if we are unable to parse a gotten data.'''

    def __init__(self, *args, **kwargs):
        Error.__init__(self, *args, **kwargs)


class PrivateGroupError(Error):
    '''Raised if the provided page is a private group.'''

    def __init__(self):
        Error.__init__(self, 'This is a private group.')


class ProfileNotAvailableError(Error):
    '''
    Raised if the provided page indicates that the user's profile has been
    deleted or is available only to authorized users.
    '''

    def __init__(self):
        Error.__init__(self, "The user's profile page is not available.")


class ServerError(Error):
    '''Raised if the provided page contains a user friendly server error.'''

    def __init__(self, server_error):
        Error.__init__(self, 'Server returned an error.')
        self.server_error = server_error


class _StopParsing(Exception):
    '''Raised to stop parsing process.'''

    def __init__(self):
        Exception.__init__(self, 'Parsing stopped.')



class WallPageParser(HTMLPageParser):
    '''Parses a vk.com wall page.

    Yeah, I know that it can be parsed more easily using a number of regular
    expressions, but it was just fun for me to use Python's HTML parser.
    Besides, parsing using an HTML parser is more steady for the site design
    changes.
    '''

    __data = None
    '''The page data.'''

    __private_data = None
    '''Various state data.'''

    __show_more_regex = re.compile(r'''
        (<span''' + HTMLPageParser.tag_attrs_regex + r'''\s*>)
        .+?
        </span>
        \s*
        <a''' + HTMLPageParser.tag_attrs_regex + '''>[^<]+</a>
        \s*
        <span''' + HTMLPageParser.tag_attrs_regex + '''
            \s+style\s*=\s*
            (?:
                "(?:[^"]*;)?\s*display\s*:\s*none\s*(?:;[^"]*)?"|
                '(?:[^']*;)?\s*display\s*:\s*none\s*(?:;[^']*)?'
            )
        ''' + HTMLPageParser.tag_attrs_regex + '''
        \s*>
    ''', re.DOTALL | re.IGNORECASE | re.VERBOSE)
    '''A regular expression for expanding a "Show more..." link.'''

    __ignore_errors = True
    '''Ignore insignificant errors.'''


    def __init__(self, ignore_errors = True):
        HTMLPageParser.__init__(self)
        self.__ignore_errors = ignore_errors


    def handle_root(self, tag, attrs, empty):
        '''Handles a tag inside of the root of the document.'''

        if tag['name'] == 'html':
            tag['new_tag_handler'] = self.handle_root
        elif tag['name'] == 'head':
            tag['new_tag_handler'] = self.__handle_head
        elif tag['name'] == 'body':
            tag['new_tag_handler'] = self.__handle_body


    def handle_root_data(self, tag, data):
        '''Handles data inside of the root of the document.'''


    def handle_root_end(self, tag):
        '''Handles end of the root of the document.'''


    def parse(self, html):
        '''Parses the specified HTML.'''

        try:
            self.__data = {}
            self.__private_data = {}

            try:
                HTMLPageParser.parse(self, html)
            except _StopParsing:
                pass


            if 'user_name' not in self.__data:
                raise ParseError('Unable to find the user name.')

            if 'posts' not in self.__data:
                raise ParseError('Unable to find the wall.')

            if not self.__data['posts'] and not self.__private_data.get('wall_is_empty'):
                raise ParseError('Unable to find wall posts.')


            for post in self.__data['posts']:
                if 'title' not in post:
                    LOG.error('Unable to find a title for post %s.', post['url'])
                    post['title'] = self.__data['user_name']


            return self.__data
        except ParseError:
            # Try to understand why we haven't found the wall on the page

            class_attr_regex_template = r'''
                \s+class=(?:
                    {name}
                    |
                    '(?:[^']*\s+)?{name}(?:\s+[^']*)?'
                    |
                    "(?:[^"]*\s+)?{name}(?:\s+[^"]*)?"
                )
            '''

            # It may be a private group
            if re.search(r'''
                <h1''' +
                    self.tag_attrs_regex + r'''
                    \s+id=(?:title|'title'|"title")''' +
                    self.tag_attrs_regex + ur'''
                \s*>
                    \s*Закрытая\s+группа
            ''', html, re.IGNORECASE | re.VERBOSE):
                raise PrivateGroupError()

            # User's profile may be deleted
            if re.search(r'''
                <div''' +
                    self.tag_attrs_regex +
                    class_attr_regex_template.format(name = 'profile_deleted') +
                    self.tag_attrs_regex + r'''
                \s*>
            ''', html, re.IGNORECASE | re.VERBOSE):
                raise ProfileNotAvailableError()



            # The server is on maintenance or returned a user friendly error -->
            match = re.search(r'''
                <title''' + self.tag_attrs_regex + ur'''\s*>
                    \s*Ошибка\s*
                </title>
                .*
                <div''' +
                    self.tag_attrs_regex +
                    class_attr_regex_template.format(name = 'body') +
                    self.tag_attrs_regex + r'''
                \s*>
                    (.*?)
                </?div
            ''', html, re.VERBOSE | re.DOTALL | re.IGNORECASE)

            if match:
                raise ServerError(
                    re.sub('<[^>]*>', '', match.group(1)).replace('<', '').replace('>', '').strip())
            # The server is on maintenance or returned a user friendly error <--


            # Other errors
            raise


    def __handle_head(self, tag, attrs, empty):
        '''Handles a tag inside of <head>.'''

        if tag['name'] == 'title':
            tag['data_handler'] = self.__handle_title_data


    def __handle_title_data(self, tag, data):
        '''Handles data inside of <title>.'''

        data = data.strip()
        if not data:
            raise ParseError('The title is empty.')

        self.__data['user_name'] = data



    def __handle_body(self, tag, attrs, empty):
        '''Handles a tag inside of <body>.'''

        if tag['name'] == 'div' and attrs.get('id') in ('group_avatar', 'profile_avatar', 'public_avatar'):
            tag['new_tag_handler'] = self.__handle_avatar
        elif tag['name'] == 'div' and attrs.get('id') == 'page_wall_posts':
            tag['new_tag_handler'] = self.__handle_page_wall_posts
            self.__data['posts'] = []
        else:
            if 'posts' in self.__data and 'user_photo' in self.__data:
                # We've found all data we need, so stop parsing to save a
                # little CPU.
                raise _StopParsing()

            tag['new_tag_handler'] = self.__handle_body


    def __handle_avatar(self, tag, attrs, empty):
        '''Handles a tag inside of <div id="profile_avatar|public_avatar".'''

        if tag['name'] == 'img' and 'src' in attrs:
            self.__data['user_photo'] = attrs['src']
        elif 'user_photo' not in self.__data:
            tag['new_tag_handler'] = self.__handle_avatar


    def __handle_page_wall_posts(self, tag, attrs, empty):
        '''Handles a tag inside of <div id="page_wall_posts">.'''

        if (
            tag['name'] == 'div' and
            attrs.get('id', '').startswith('post') and
            len(attrs['id']) > len('post') and
            self.__has_class(attrs, 'post')
        ):
            if empty:
                raise ParseError('Post "{0}" div tag is empty.', attrs['id'])

            self.__add_post( attrs['id'][len('post'):] )

            tag['new_tag_handler'] = self.__handle_post
            tag['end_tag_handler'] = self.__handle_post_end
        elif tag['name'] == 'div' and attrs.get('id') == 'page_no_wall':
            self.__private_data['wall_is_empty'] = True
        else:
            tag['new_tag_handler'] = self.__handle_page_wall_posts


    def __handle_post(self, tag, attrs, empty):
        '''Handles a tag inside of <div id="post...">.'''

        if tag['name'] == 'div' and self.__has_class(attrs, 'post_table'):
            tag['new_tag_handler'] = self.__handle_post_table
        else:
            if not self.__get_cur_post()['text']:
                tag['new_tag_handler'] = self.__handle_post


    def __handle_post_table(self, tag, attrs, empty):
        '''Handles a tag inside of <div class="post_table">.'''

        if tag['name'] == 'div' and self.__has_class(attrs, 'post_info'):
            tag['new_tag_handler'] = self.__handle_post_table_info


    def __handle_post_table_info(self, tag, attrs, empty):
        '''Handles a tag inside of <div class="post_table"><div class="post_info">.'''

        if tag['name'] == 'div' and self.__has_class(attrs, 'text', 'wall_text'):
            tag['new_tag_handler'] = self.__handle_post_text
        elif tag['name'] == 'div' and self.__has_class(attrs, 'replies'):
            tag['new_tag_handler'] = self.__handle_post_replies
        else:
            tag['new_tag_handler'] = self.__handle_post_table_info


    def __handle_post_text(self, tag, attrs, empty):
        '''Handles a tag inside of <div class="post_table"><div class="post_info"><div class="wall_text">.'''

        if tag['name'] == 'a' and self.__has_class(attrs, 'author'):
            tag['data_handler'] = self.__handle_post_author
        elif tag['name'] == 'div' or tag['name'] == 'span' and attrs.get('class') == 'explain':
            self.__handle_post_data_container(tag, attrs, empty)


    def __handle_post_author(self, tag, data):
        '''Handles data inside of a post author tag.'''

        data = data.strip()

        if data:
            self.__get_cur_post()['title'] = data


    def __handle_post_data_container(self, tag, attrs, empty):
        '''Handles a tag inside of post data tag.'''

        if tag['name'] == 'div' and self.__has_class(attrs, 'page_post_queue_narrow'):
            pass # Ignore image thumbnails
        else:
            stripped_tag = self.__strip_tag(tag['name'], attrs, empty)

            if stripped_tag:
                def end_tag_handler(tag):
                    self.__get_cur_post()['text'] += stripped_tag[1]

                self.__get_cur_post()['text'] += stripped_tag[0]
                tag['new_tag_handler'] = self.__handle_post_data_container
                tag['data_handler'] = self.__handle_post_data

                if empty:
                    end_tag_handler(tag)
                else:
                    tag['end_tag_handler'] = end_tag_handler


    def __handle_post_data(self, tag, data):
        '''Handles data inside of post data tag.'''

        self.__get_cur_post()['text'] += data



    def __handle_post_replies(self, tag, attrs, empty):
        '''Handles a tag inside of <div class="post_table"><div class="post_info"><div class="replies">.'''

        if tag['name'] == 'div' and self.__has_class(attrs, 'reply_link_wrap'):
            tag['new_tag_handler'] = self.__handle_post_link
        else:
            tag['new_tag_handler'] = self.__handle_post_replies


    def __handle_post_link(self, tag, attrs, empty):
        '''Handles a tag inside of <div class="post_table"><div class="post_info"><div class="replies"><div class="reply_link_wrap">.'''

        if tag['name'] == 'span' and self.__has_class(attrs, 'rel_date'):
            tag['data_handler'] = self.__handle_post_date
        else:
            tag['new_tag_handler'] = self.__handle_post_link


    def __handle_post_date(self, tag, data):
        '''Handles data inside of post replies tag.'''

        replacements = (
            ( 'jan.', '1'  ),
            ( 'feb.', '2'  ),
            ( 'mar.', '3'  ),
            ( 'apr.', '4'  ),
            ( 'may',  '5'  ),
            ( 'jun.', '6'  ),
            ( 'jul.', '7'  ),
            ( 'aug.', '8'  ),
            ( 'sep.', '9'  ),
            ( 'oct.', '10' ),
            ( 'nov.', '11' ),
            ( 'dec.', '12' ),

            ( 'янв', '1'  ),
            ( 'фев', '2'  ),
            ( 'мар', '3'  ),
            ( 'апр', '4'  ),
            ( 'мая', '5'  ),
            ( 'июн', '6'  ),
            ( 'июл', '7'  ),
            ( 'авг', '8'  ),
            ( 'сен', '9'  ),
            ( 'окт', '10' ),
            ( 'ноя', '11' ),
            ( 'дек', '12' ),

            ( 'два',     '2' ),
            ( 'две',     '2' ),
            ( 'три',     '3' ),
            ( 'четыре',  '4' ),
            ( 'пять',    '5' ),
            ( 'шесть',   '6' ),
            ( 'семь',    '7' ),
            ( 'восемь',  '8' ),
            ( 'девять',  '9' ),
            ( 'десять', '10' ),

            ( 'two',   '2' ),
            ( 'three', '3' ),
            ( 'four',  '4' ),
            ( 'five',  '5' ),
            ( 'six',   '6' ),
            ( 'seven', '7' ),
            ( 'eight', '8' ),
            ( 'nine',  '9' ),
            ( 'ten',  '10' ),

            ( 'вчера',   'yesterday' ),
            ( 'сегодня', 'today' ),
            ( ' в ',     ' at ' )
        )

        date_string = data.strip().lower()

        is_pm = date_string.endswith(' pm')
        if date_string.endswith(' am') or date_string.endswith(' pm'):
            date_string = date_string[:-3]

        tz_delta = datetime.timedelta(hours = 4) # MSK timezone
        today = datetime.datetime.utcnow() + tz_delta

        for token, replacement in replacements:
            date_string = date_string.replace(token, replacement)

        try:
            match = re.match(ur'(\d+ ){0,1}([^ ]+) (?:назад|ago)', date_string)

            if match:
                value = match.group(1)
                if value:
                    value = int(value.strip())
                else:
                    value = 1

                unit = match.group(2)

                if unit in ('секунд', 'секунду', 'секунды', 'second', 'seconds'):
                    date = today - datetime.timedelta(seconds = value)
                elif unit in ('минут', 'минуту', 'минуты', 'minute', 'minutes'):
                    date = today - datetime.timedelta(minutes = value)
                elif unit in ('час', 'часа', 'часов', 'hour', 'hours'):
                    date = today - datetime.timedelta(hours = value)
                elif unit in ('день', 'дня', 'дней', 'day', 'days'):
                    date = today - datetime.timedelta(days = value)
                elif unit in ('неделю', 'недели', 'недель', 'week', 'weeks'):
                    date = today - datetime.timedelta(weeks = value)
                else:
                    raise Error('Invalid time dimension: {0}.', unit)
            else:
                try:
                    date = datetime.datetime.strptime(date_string, 'today at %H:%M')
                    date = datetime.datetime.combine(today, date.time())
                except ValueError:
                    try:
                        date = datetime.datetime.strptime(date_string, 'yesterday at %H:%M')
                        date = datetime.datetime.combine(today - datetime.timedelta(days = 1), date.time())
                    except ValueError:
                        try:
                            date = datetime.datetime.strptime('{0} {1}'.format(today.year, date_string), '%Y %d %m at %H:%M')
                        except ValueError:
                            date = datetime.datetime.strptime(date_string, '%d %m %Y')
                            date += tz_delta

            if is_pm:
                date += datetime.timedelta(hours = 12)

            date -= tz_delta

            if date - datetime.timedelta(minutes = 1) > today:
                if date - datetime.timedelta(days = 1) <= today:
                    date -= datetime.timedelta(days = 1)
                else:
                    last_year_date = datetime.datetime(date.year - 1, date.month, date.day, date.hour, date.minute, date.second, date.microsecond, date.tzinfo)
                    if last_year_date <= today:
                        date = last_year_date

            self.__get_cur_post()['date'] = date
        except Exception as e:
            if self.__ignore_errors:
                LOG.exception('Failed to parse date %s.', data)
            else:
                raise e



    def __handle_post_end(self, tag):
        '''Handles end of <div id="post...">.'''

        cur_post = self.__get_cur_post()

        # Expanding the post contents
        cur_post['text'] = self.__show_more_regex.sub(r'\1', cur_post['text'])

        # Cut off video counters which are broken due to stripping class
        # attributes
        cur_post['text'] = re.sub(r'<div>\s*<span>(?:\d+:)?\d+:\d+</span>\s*</div>', '', cur_post['text'])

        cur_post['text'] = cur_post['text'].strip()



    def __add_post(self, post_id):
        '''Adds a new post to the wall.'''

        self.__data['posts'].append({
            'id':   post_id,
            'url':  constants.VK_URL + 'wall' + post_id,
            'text': '',
        })


    def __get_cur_post(self):
        '''Returns current post.'''

        return self.__data['posts'][-1]


    def __has_class(self, attrs, *class_names):
        '''
        Checks whether a tag with the specified attributes has at least one of
        the specified classes.
        '''

        tag_classes = set(attrs.get('class', '').strip().split(' '))
        return bool(tag_classes.intersection(set(class_names)))


    def __strip_tag(self, tag_name, attrs, empty):
        '''
        Returns a tuple of strings where the first is the specified tag which
        have only attributes allowed for RSS and the second is a tag close
        string. Returns None if the tag is not allowed in RSS at all.

        Produces only a lazy check. All other work is left for RSS reader.
        '''

        if tag_name in ('body', 'head', 'html', 'script'):
            # Reject this tags
            return

        tag_data = '<' + tag_name

        # Stripping the tag attributes -->
        for attr, value in attrs.iteritems():
            if (
                tag_name == 'img' and attr == 'src' or
                tag_name == 'a' and attr == 'href'
            ):
                if not re.match('[a-z]+://', value):
                    value = constants.VK_URL + value[int(value.startswith('/')):]

                away_to_prefix = constants.VK_URL + 'away.php?to='
                if value.startswith(away_to_prefix):
                    value = urllib.unquote(value.split('&')[0][len(away_to_prefix):])
            elif tag_name == 'a' and attr == 'onclick' and not attrs.get('href', '').strip():
                if value.startswith('playAudio'):
                    # Ignore this link and all its contents - we'll try to get
                    # the link from other tags.
                    return

                # Trying to obtain a link from the JavaScript handler
                match = re.search('"(http://[^"]+)"' + '|' "'(http://[^']+)'", value)

                if match:
                    attr = 'href'
                    value = match.group(1)
                else:
                    continue
            elif attr in ('id', 'class') or attr.startswith('on'):
                continue

            tag_data += ' {0}="{1}"'.format(attr, cgi.escape(value, quote = True))
        # Stripping the tag attributes <--

        return (
            tag_data + (' />' if empty else '>'),
            '' if empty else '</{0}>'.format(tag_name)
        )
