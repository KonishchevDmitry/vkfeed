'''A convenient class for parsing HTML pages.'''

from HTMLParser import HTMLParser
import logging
import re


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


    __script_regex = re.compile('<script' + tag_attrs_regex + '>.*?</script>', re.DOTALL | re.IGNORECASE)
    '''A regular expression for matching scripts.'''

    __invalid_tag_attrs_regex = re.compile(r'''
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
        (
          [^\s/>]
        )
    ''', re.VERBOSE)
    '''
    A regular expression for matching a common error in specifying tag
    attributes.
    '''

    __misopened_tag_regex = re.compile(r'<(br|hr|img)' + tag_attrs_regex + r'\s*>', re.IGNORECASE)
    '''A regular expression for matching opened tags that should be closed.'''


    __tag_stack = None
    '''Stack of currently opened HTML tags.'''


    def __init__(self):
        HTMLParser.__init__(self)


    def handle_data(self, data):
        '''Handles data.'''

        tag = self.__get_cur_tag()
        handler = tag.get('data_handler')

        if handler is not None:
            # TODO
            logging.debug('Data "%s" in "%s" with handler %s.',
                data, tag['name'], handler.func_name)

            handler(self.__get_cur_tag(), data)


    def handle_endtag(self, tag_name):
        '''Handles end of a tag.'''

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
                logging.debug('Dropping excess end tag "%s"...', tag_name)

        # TODO
        logging.debug('Current tag: %s', self.__get_cur_tag())


    def handle_root_data(self, tag, data):
        '''Handles data inside of the root of the document.'''

        logging.debug('%s', data)


    def handle_root_new_tag(self, tag, attrs, empty):
        '''Handles a tag inside of the root of the document.'''

        logging.debug('<%s %s%s>', tag['name'], attrs, '/' if empty else '')
        tag['new_tag_handler'] = self.handle_root_new_tag
        tag['data_handler'] = self.handle_root_data
        tag['end_tag_handler'] = self.handle_root_tag_end


    def handle_root_tag_end(self, tag):
        '''Handles end of the root of the document.'''

        logging.debug('</%s>', tag['name'])


    def handle_startendtag(self, tag, attrs):
        '''Handles start of an XHTML-style empty tag.'''

        self.__handle_start_tag(tag, attrs, True)


    def handle_starttag(self, tag, attrs):
        '''Handles start of a tag.'''

        self.__handle_start_tag(tag, attrs, False)


    def reset(self):
        '''Resets the parser.'''

        HTMLParser.reset(self)

        self.__tag_stack = [{
            # Add fake root tag
            'name':              None,
            'new_tag_handler':   self.handle_root_new_tag,
            'data_handler':      self.handle_root_data,
            'end_tag_handler':   self.handle_root_tag_end,
        }]


    def parse(self, html):
        '''Parses the specified HTML page.'''

        # Fixing various things that may confuse the python's HTML parser
        html = self.__script_regex.sub('', html)
        html = self.__invalid_tag_attrs_regex.sub(r'\1 \2', html)
        html = self.__misopened_tag_regex.sub(r'<\1/>', html)

        # Run the parser
        self.reset()
        self.feed(html)
        self.close()

        # Close all unclosed tags
        for tag in self.__tag_stack[1:]:
            self.__close_tag(tag, True)


    def __close_tag(self, tag, forced = False):
        '''Forces closing of an unclosed tag.'''

        if forced:
            logging.debug('Force closing of unclosed tag "%s".', tag['name'])

        if 'end_tag_handler' in tag:
            tag['end_tag_handler'](tag)


    def __get_cur_tag(self):
        '''Returns currently opened tag.'''

        return self.__tag_stack[-1]


    def __handle_start_tag(self, tag_name, attrs, empty):
        '''Handles start of any tag.'''

        tag = { 'name': tag_name }
        handler = self.__get_cur_tag().get('new_tag_handler')

        if handler is not None:
            attrs = self.__parse_attrs(attrs)

            # TODO
            logging.debug('Start tag: %s %s with handler %s.',
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

