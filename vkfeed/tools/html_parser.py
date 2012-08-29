'''A convenient class for parsing HTML pages.'''

from __future__ import unicode_literals

from HTMLParser import HTMLParser
import logging
import re

from vkfeed.core import Error

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)


class HTMLPageParser(HTMLParser):
    '''A convenient class for parsing HTML pages.'''

    tag_name_regex = '[a-zA-Z][-.a-zA-Z0-9:_]*'
    '''A regular expression for tag name.'''

    attribute_name_regex = tag_name_regex
    '''A regular expression for attribute name.'''

    tag_attrs_regex = re.sub(r'\s*', '', r'''
        (?:\s+
          ''' + attribute_name_regex + r'''
          (?:\s*=\s*
            (?:
              '[^']*'
              |"[^"]*"
              |[^'"/>\s]+
            )
          )?
        )*
    ''')
    '''A regular expression for tag attributes.'''

    script_regex = re.compile('<script' + tag_attrs_regex + '>.*?</script>', re.DOTALL | re.IGNORECASE)
    '''A regular expression for matching scripts.'''


    __invalid_tag_attr_spacing_regex = re.compile(r'''
        (
          # Tag name
          <''' + tag_name_regex + r'''

          # Zero or several attributes
          ''' + tag_attrs_regex + r'''

          # Two attributes without a space between them
          \s+                                # whitespace before attribute name
          ''' + attribute_name_regex + r'''  # attribute name
          \s*=\s*                            # value indicator
          (?:
            '[^']*'                          # LITA-enclosed value
            |"[^"]*"                         # LIT-enclosed value
          )
        )
        ([^\s>])                             # Do not include / to make the preparation replacement for __invalid_tag_attr_regex
    ''', re.VERBOSE)
    '''
    A regular expression for matching a common error in specifying tag
    attributes.
    '''

    __invalid_tag_attr_regex = re.compile(r'''
        (
          # Tag name
          <''' + tag_name_regex + r'''

          # Zero or several attributes
          ''' + tag_attrs_regex + r'''
        )
        \s+(?:
            # Invalid characters instead of an attribute
            [^\sa-zA-Z/>]\S*
            |
            # Sole slash
            /\s
            |
            # Invalid characters starting from slash instead of an attribute
            /[^>\s]+
        )
    ''', re.VERBOSE)
    '''
    A regular expression for matching HTML errors like:
    <a class="app photo"/app2322149_58238998?from_id=2381857&loc=addneighbour onclick="return cur.needLoginBox()">
    '''


    __empty_tags = 'area|base|basefont|br|col|frame|hr|img|input|link|meta|param'
    '''A list of all HTML empty tags.'''

    __misopened_tag_regex = re.compile(r'<(' + __empty_tags + tag_attrs_regex + r')\s*>', re.IGNORECASE)
    '''A regular expression for matching opened tags that should be closed.'''


    __tag_stack = None
    '''A stack of currently opened HTML tags.'''

    __cur_data = None
    '''
    Accumulates data between handle_charref(), handle_entityref() and
    handle_data() calls.
    '''


    def __init__(self):
        HTMLParser.__init__(self)


    def handle_charref(self, name):
        '''Handles a character reference of the form &#ref;.'''

        self.__accumulate_data('&#' + name + ';')


    def handle_data(self, data):
        '''Handles data.'''

        self.__accumulate_data(data)


    def handle_endtag(self, tag_name):
        '''Handles end of a tag.'''

        self.__handle_data_if_exists()

        if self.__get_cur_tag()['name'] == tag_name:
            self.__close_tag(self.__tag_stack.pop())
        else:
            for tag_id in xrange(len(self.__tag_stack) - 1, -1, -1):
                if self.__tag_stack[tag_id]['name'] == tag_name:
                    for tag in reversed(self.__tag_stack[tag_id + 1:]):
                        self.__close_tag(tag, forced = True)
                        self.__tag_stack.pop()

                    self.__close_tag(self.__tag_stack.pop())
                    break
            else:
                LOG.debug('Dropping excess end tag "%s"...', tag_name)


    def handle_entityref(self, name):
        '''Handles a general entity reference of the form &name;.'''

        self.__accumulate_data('&' + name + ';')


    def handle_root_data(self, tag, data):
        '''Handles data inside of the root of the document.'''

        LOG.debug('%s', data)


    def handle_root(self, tag, attrs, empty):
        '''Handles a tag inside of the root of the document.'''

        LOG.debug('<%s %s%s>', tag['name'], attrs, '/' if empty else '')
        tag['new_tag_handler'] = self.handle_root
        tag['data_handler'] = self.handle_root_data
        tag['end_tag_handler'] = self.handle_root_end


    def handle_root_end(self, tag):
        '''Handles end of the root of the document.'''

        LOG.debug('</%s>', tag['name'])


    def handle_startendtag(self, tag, attrs):
        '''Handles start of an XHTML-style empty tag.'''

        self.__handle_data_if_exists()
        self.__handle_start_tag(tag, attrs, True)


    def handle_starttag(self, tag, attrs):
        '''Handles start of a tag.'''

        self.__handle_data_if_exists()
        self.__handle_start_tag(tag, attrs, False)


    def reset(self):
        '''Resets the parser.'''

        HTMLParser.reset(self)

        self.__tag_stack = [{
            # Add fake root tag
            'name':              None,
            'new_tag_handler':   self.handle_root,
            'data_handler':      self.handle_root_data,
            'end_tag_handler':   self.handle_root_end,
        }]


    def parse(self, html):
        '''Parses the specified HTML page.'''

        html = self.__fix_html(html)

        self.reset()

        try:
            # Run the parser
            self.feed(html)
            self.close()
        finally:
            # Close all unclosed tags
            for tag in self.__tag_stack[1:]:
                self.__close_tag(tag, True)


    def __accumulate_data(self, data):
        '''
        Accumulates data between handle_charref(), handle_entityref() and
        handle_data() calls.
        '''

        if self.__cur_data is None:
            self.__cur_data = data
        else:
            self.__cur_data += data


    def __close_tag(self, tag, forced = False):
        '''Forces closing of an unclosed tag.'''

        if forced:
            LOG.debug('Force closing of unclosed tag "%s".', tag['name'])
        else:
            LOG.debug('Tag %s closed.', tag)

        if 'end_tag_handler' in tag:
            tag['end_tag_handler'](tag)

        LOG.debug('Current tag: %s.', self.__get_cur_tag())


    def __fix_html(self, html):
        '''Fixes various things that may confuse the Python's HTML parser.'''

        html = self.script_regex.sub('', html)

        loop_replacements = (
            lambda html: self.__invalid_tag_attr_spacing_regex.subn(r'\1 \2', html),
            lambda html: self.__invalid_tag_attr_regex.subn(r'\1 ', html),
        )

        for loop_replacement in loop_replacements:
            for i in xrange(0, 1000):
                html, changed = loop_replacement(html)

                if not changed:
                    break
            else:
                raise Error('Too many errors in the HTML or infinite loop.')

        html = self.__misopened_tag_regex.sub(r'<\1 />', html)

        return html


    def __get_cur_tag(self):
        '''Returns currently opened tag.'''

        return self.__tag_stack[-1]


    def __handle_data_if_exists(self):
        '''Handles accumulated data (if exists).'''

        data = self.__cur_data
        if data is None:
            return

        self.__cur_data = None

        tag = self.__get_cur_tag()
        handler = tag.get('data_handler')

        if handler is not None:
            LOG.debug('Data "%s" in "%s" with handler %s.',
                data, tag['name'], handler.func_name)

            handler(tag, data)


    def __handle_start_tag(self, tag_name, attrs, empty):
        '''Handles start of any tag.'''

        tag = { 'name': tag_name }
        handler = self.__get_cur_tag().get('new_tag_handler')

        if handler is not None:
            attrs = self.__parse_attrs(attrs)

            LOG.debug('Start tag: %s %s with handler %s.',
                tag, attrs, handler.func_name)

            handler(tag, attrs, empty)

        if not empty:
            self.__tag_stack.append(tag)


    def __parse_attrs(self, attrs_tuple):
        '''Converts tag attributes from a tuple to a dictionary.'''

        attrs = {}

        for attr, value in attrs_tuple:
            attrs[attr.lower()] = value

        return attrs
