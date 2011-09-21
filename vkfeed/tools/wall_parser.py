# -*- coding: utf-8 -*-

'''Parses a vk.com wall page.'''

import cgi
import logging
import re
import urllib

from vkfeed import constants
from vkfeed.core import Error
from vkfeed.tools.html_parser import HTMLPageParser

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)


WALL_TYPE_PROFILE_PAGE = "profile-page"
"""A user profile page."""

WALL_TYPE_WALL_PAGE = "wall-page"
"""A plain wall page."""


class ParseError(Error):
    '''Raised if we are unable to parse a gotten data.'''

    def __init__(self, *args, **kwargs):
        Error.__init__(self, *args, **kwargs)


class PrivateGroupError(Error):
    '''Raised if the provided page is a private group.'''

    def __init__(self):
        Error.__init__(self, "This is a private group.")


class ProfileDeletedError(Error):
    '''
    Raised if the provided page indicates that the user's profile has been
    deleted.
    '''

    def __init__(self):
        Error.__init__(self, "The user's profile page has been deleted.")


class ServerError(Error):
    '''Raised if the provided page contains a user friendly server error.'''

    def __init__(self, server_error):
        Error.__init__(self, "Server returned an error.")
        self.server_error = server_error


class _StopParsing(Exception):
    '''Raised to stop parsing process.'''

    def __init__(self):
        Exception.__init__(self, "Parsing stopped.")



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


    def __init__(self):
        HTMLPageParser.__init__(self)


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


    def parse(self, html, wall_type = WALL_TYPE_PROFILE_PAGE):
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


            if 'user_photo' not in self.__data and wall_type != WALL_TYPE_WALL_PAGE:
                LOG.error('Unable to find a user photo on the page.')

            for post in self.__data['posts']:
                if 'title' not in post:
                    LOG.error('Unable to find a title for post %s.', post['url'])
                    post['title'] = self.__data['user_name']


            return self.__data
        except ParseError:
            # Try to understand why we haven't found the wall on the page

            class_attr_regex_template = r'''
                \s+class=(?:
                    %(class)s
                    |
                    '(?:[^']*\s+)?%(class)s(?:\s+[^']*)?'
                    |
                    "(?:[^"]*\s+)?%(class)s(?:\s+[^"]*)?"
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
                    class_attr_regex_template % { 'class': 'profile_deleted' } +
                    self.tag_attrs_regex + r'''
                \s*>
            ''', html, re.IGNORECASE | re.VERBOSE):
                raise ProfileDeletedError()



            # The server is on maintenance or returned a user friendly error -->
            match = re.search(r'''
                <title''' + self.tag_attrs_regex + ur'''\s*>
                    \s*Ошибка\s*
                </title>
                .*
                <div''' +
                    self.tag_attrs_regex +
                    class_attr_regex_template % { 'class': 'body' } +
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
                raise ParseError('Post "%s" div tag is empty.', attrs['id'])

            self.__add_post( attrs['id'][len('post'):] )

            tag['new_tag_handler'] = self.__handle_post
            tag['end_tag_handler'] = self.__handle_post_end
        elif tag['name'] == 'div' and attrs.get('id') == 'page_no_wall':
            self.__private_data['wall_is_empty'] = True
        else:
            tag['new_tag_handler'] = self.__handle_page_wall_posts


    def __handle_post(self, tag, attrs, empty):
        '''Handles a tag inside of <div id="post...">.'''

        if tag['name'] == 'table' and self.__has_class(attrs, 'post_table'):
            tag['new_tag_handler'] = self.__handle_post_table
        else:
            if not self.__get_cur_post()['text']:
                tag['new_tag_handler'] = self.__handle_post


    def __handle_post_table(self, tag, attrs, empty):
        '''Handles a tag inside of <table class="post_table">.'''

        if tag['name'] == 'tr':
            tag['new_tag_handler'] = self.__handle_post_table_row


    def __handle_post_table_row(self, tag, attrs, empty):
        '''Handles a tag inside of <table class="post_table"><tr>.'''

        if tag['name'] == 'td' and self.__has_class(attrs, 'info'):
            tag['new_tag_handler'] = self.__handle_post_table_row_info


    def __handle_post_table_row_info(self, tag, attrs, empty):
        '''Handles a tag inside of <table class="post_table"><tr><td class="info">.'''

        if tag['name'] == 'div' and self.__has_class(attrs, 'text', 'wall_text'):
            tag['new_tag_handler'] = self.__handle_post_text
        else:
            tag['new_tag_handler'] = self.__handle_post_table_row_info


    def __handle_post_text(self, tag, attrs, empty):
        '''Handles a tag inside of <table class="post_table"><tr><td class="info"><div class="wall_text">.'''

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

            tag_data += u' %s="%s"' % (attr, cgi.escape(value, quote = True))
        # Stripping the tag attributes <--

        return (
            tag_data + '%s>' % (' /' if empty else ''),
            '' if empty else '</%s>' % tag_name
        )

