#!/usr/bin/env python

'''Tests utils module.'''

from __future__ import unicode_literals

import unittest

import vkfeed.utils


class TestUtils(unittest.TestCase):
    '''Tests utils module.'''

    def test_zero_subscribers(self):
        '''Tests utils.zero_subscribers().'''

        self.assertFalse(vkfeed.utils.zero_subscribers(
            'Mozilla/5.0 (compatible; FriendFeedBot/0.1; +Http://friendfeed.com/about/bot; 9 subscribers; feed-id=1323910685477517368)'))

        self.assertFalse(vkfeed.utils.zero_subscribers(
            'RSS.I.UA - Robot Verter (v1.1; contact: support@i.ua; url: http://vkontakte-feed.appspot.com/feed/id5698188/wall; 1 subscriber)'))
        self.assertTrue(vkfeed.utils.zero_subscribers(
            'RSS.I.UA - Robot Verter (v1.1; contact: support@i.ua; url: http://vkontakte-feed.appspot.com/feed/id5698188/wall; 0 subscriber)'))

        self.assertFalse(vkfeed.utils.zero_subscribers(
            'LiveJournal.com (webmaster@livejournal.com; for http://www.livejournal.com/users/zzzperm_vk/; 1 readers)'))
        self.assertTrue(vkfeed.utils.zero_subscribers(
            'LiveJournal.com (webmaster@livejournal.com; for http://www.livejournal.com/users/zzzperm_vk/; 0 readers)'))
        self.assertTrue(vkfeed.utils.zero_subscribers(
            'LiveJournal.com (webmaster@livejournal.com; for http://www.livejournal.com/users/zzzperm_vk/; 0 reader)'))

        self.assertTrue(vkfeed.utils.zero_subscribers(
            'Netvibes (http://www.netvibes.com/; 0 subscribers; feedID: 19374716)'))

        self.assertFalse(vkfeed.utils.zero_subscribers(
            'Mozilla/5.0 (compatible; YandexBlogs/0.99; robot; B; +http://yandex.com/bots) 1 readers'))
        self.assertTrue(vkfeed.utils.zero_subscribers(
            'Mozilla/5.0 (compatible; YandexBlogs/0.99; robot; B; +http://yandex.com/bots)0 readers'))

        self.assertFalse(vkfeed.utils.zero_subscribers(
            'Feedfetcher-Google; (+http://www.google.com/feedfetcher.html; feed-id=7298227410921540799)'))
        self.assertFalse(vkfeed.utils.zero_subscribers(
            'Feedfetcher-Google; (+http://www.google.com/feedfetcher.html; 10 subscribers; feed-id=9132423496004288118)'))
        self.assertTrue(vkfeed.utils.zero_subscribers(
            'Feedfetcher-Google; (+http://www.google.com/feedfetcher.html; 0 subscribers; feed-id=9132423496004288118)'))


if __name__ == '__main__':
    unittest.main()
