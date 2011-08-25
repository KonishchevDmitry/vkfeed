# -*- coding: utf-8 -*-

'''Various core classes and functions.'''


class Error(Exception):
    '''Base class for all exceptions thrown by the application.'''

    def __init__(self, error, *args):
        if args:
            Exception.__init__(self, unicode(error) % args)
        else:
            Exception.__init__(self, unicode(error))

