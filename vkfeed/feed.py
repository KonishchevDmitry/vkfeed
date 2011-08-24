#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Generates an RSS feed."""

import httplib
import logging
import re

from google.appengine.ext import webapp

from vkfeed.core import Error
import vkfeed.util
from vkfeed.wall_parser import WallPageParser, ParseError


class Feed(webapp.RequestHandler):
    """Generates an RSS feed."""


    def get(self, profile_name):
        """Processes the request."""

# TODO: check profile_name
        logging.info("Requested feed for '%s'.", profile_name)

        url = "http://vk.com/" + profile_name

        try:
            profile_page = vkfeed.util.fetch_url(url)

            try:
                data = WallPageParser().parse(profile_page)
            except ParseError, e:
                raise Error(
                    "Got unexpected content from server. "
                    "Please make sure you specified a valid account ID. "
                    "If you've specified a valid account ID, please contact "
                    "<a href='mailto:Dmitry Konishchev &lt;konishchev@gmail.com&gt;'>konishchev@gmail.com</a>." # TODO
                )

            data["url"] = url
            feed = self.__generate_feed(data)
        except Error, e:
            logging.error("Unable to generate a feed for '%s': %s.", url, e)

            self.error(httplib.BAD_GATEWAY)
            self.response.out.write(vkfeed.util.render_template("feed_error.html", {
                "feed_source": url,
                "error":       e
            }))
        else:
            self.response.out.write(feed)


    # TODO
    def __generate_feed(self, data):
        """Generates a feed from a parsed data."""

        import datetime
        from PyRSS2Gen import PyRSS2Gen

        rss = PyRSS2Gen.RSS2(
            title = data["user"],
            link = data["url"],
            description = u"Сообщения со стены пользователя %s" % data["user"],

            language = "ru",

            #language = None,
            #copyright = None,
            #managingEditor = None,
            #webMaster = None,
            #pubDate = None,  # a datetime, *in* *GMT*
            #lastBuildDate = None, # a datetime
            #
            #categories = None, # list of strings or Category
            #generator = _generator_name,
            #docs = "http://blogs.law.harvard.edu/tech/rss",
            #cloud = None,    # a Cloud
            #ttl = None,      # integer number of minutes

            #image = None,     # an Image
            #rating = None,    # a string; I don't know how it's used
            #textInput = None, # a TextInput
            #skipHours = None, # a SkipHours with a list of integers
            #skipDays = None,  # a SkipDays with a list of strings

            #items = None,     # list of RSSItems

            lastBuildDate = datetime.datetime.now(),

            items = [
                 #title = None,  # string
                 #link = None,   # url as string
                 #description = None, # string
                 #author = None,      # email address as string
                 #categories = None,  # list of string or Category
                 #comments = None,  # url as string
                 #enclosure = None, # an Enclosure
                 #guid = None,    # a unique string
                 #pubDate = None, # a datetime
                 #source = None,  # a Source
                PyRSS2Gen.RSSItem(
                  title = data["user"],
                  link = "http://no-url.com/",
                  description = post["text"],
                  guid = PyRSS2Gen.Guid("http://" + post["id"]),
                  pubDate = datetime.datetime(2003, 9, 6, 21, 31)
                )
            for post in data["posts"] ])

        return rss.to_xml("utf-8")

