#!/usr/bin/env python

'''Tests HTMLPageParser.'''

from __future__ import unicode_literals

import os
import unittest

from vkfeed.tools.html_parser import HTMLPageParser


class TestHTMLPageParser(unittest.TestCase):
    '''Tests HTMLPageParser.'''


    def test(self):
        '''Testing HTMLPageParser.'''

        page_dir = 'html_parser'

        for page_name in os.listdir(page_dir):
            page_path = os.path.join(page_dir, page_name)
            print 'Testing "{0}"...'.format(page_path)
            HTMLPageParser().parse(open(page_path).read().decode('utf-8'))



if __name__ == '__main__':
    # For test debugging
    #import logging
    #logging.getLogger().setLevel(logging.DEBUG)
    #logging.getLogger("vkfeed").addHandler(logging.StreamHandler())

    unittest.main()

