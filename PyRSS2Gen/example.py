# An example of how to generate a feed by hand.

import datetime
import PyRSS2Gen

rss = PyRSS2Gen.RSS2(
    title = "Andrew's PyRSS2Gen feed",
    link = "http://www.dalkescientific.com/Python/PyRSS2Gen.html",
    description = "The latest news about PyRSS2Gen, a "
                  "Python library for generating RSS2 feeds",

    lastBuildDate = datetime.datetime.now(),

    items = [
       PyRSS2Gen.RSSItem(
         title = "PyRSS2Gen-0.0 released",
         link = "http://www.dalkescientific.com/news/030906-PyRSS2Gen.html",
         description = "Dalke Scientific today announced PyRSS2Gen-0.0, "
                       "a library for generating RSS feeds for Python.  ",
         guid = PyRSS2Gen.Guid("http://www.dalkescientific.com/news/"
                          "030906-PyRSS2Gen.html"),
         pubDate = datetime.datetime(2003, 9, 6, 21, 31)),
       PyRSS2Gen.RSSItem(
         title = "Thoughts on RSS feeds for bioinformatics",
         link = "http://www.dalkescientific.com/writings/diary/"
                "archive/2003/09/06/RSS.html",
         description = "One of the reasons I wrote PyRSS2Gen was to "
                       "experiment with RSS for data collection in "
                       "bioinformatics.  Last year I came across...",
         guid = PyRSS2Gen.Guid("http://www.dalkescientific.com/writings/"
                               "diary/archive/2003/09/06/RSS.html"),
         pubDate = datetime.datetime(2003, 9, 6, 21, 49)),
    ])

rss.write_xml(open("pyrss2gen.xml", "w"))
