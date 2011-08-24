# unittest?  What's that?
#
# You'll need Mark Pilgrim's feed_parser, from
#  http://diveintomark.org/projects/feed_parser/
# The test takes a structure, converts it to XML,
# reads it back using feed_parser, and compares
# the two stuctures.  feed_parser doesn't handle
# everything, so I needed to filter some items.
# I also haven't tested everything.

import datetime
import PyRSS2Gen
import feedparser

rss = PyRSS2Gen.RSS2(
    "This is a test",
    "http://www.dalkescientific.com/",
    "To be or not to be.  That is the question.",

    language = "en-US",
    copyright = "Copyright (c) 2003, by me",
    managingEditor = "here@there (everywhere)",
    webMaster = "Spider Man",
    pubDate = datetime.datetime(2000, 11, 20, 23, 45, 19),
    lastBuildDate = datetime.datetime(2001, 12, 25, 22, 51, 49),
    categories = ["live", "love", "larf", "loaf"],

    cloud = PyRSS2Gen.Cloud("rpc.sys.com", 80, "/RPC2", "pingMe", "soap"),
                       
    ttl = 10,
    image = PyRSS2Gen.Image("http://there/", "THERE!", "link?",
                            25, 94, "some description"),
    rating = "For all audiences",

    textInput = PyRSS2Gen.TextInput("Qwerty", "Shrdlu", "Etaoin",
                                    "http://some/link"),
    skipDays = PyRSS2Gen.SkipDays(["Monday", "Thursday"]),
    skipHours = PyRSS2Gen.SkipHours([0, 5, 22]),

    items = [PyRSS2Gen.RSSItem(
                "Chapter 1", "http://xe.com/",
                "How to convert money.",
                author = "x@xe",
                # categories
                comments = "http://slashdot.org",
                # enclosure
                guid = "http://asdfghjk/",
                pubDate = datetime.datetime(1999, 1, 30),
                source = PyRSS2Gen.Source("ftp://x.y/",
                                          "Quotes of the Day"),
                          
                ),
             PyRSS2Gen.RSSItem("Chapter 2", "http://acm.org/",
                               "AT&T is <Ma Bell>.",
                               guid = PyRSS2Gen.Guid(guid = "12345", isPermaLink = False),
                               ),
             ])

def _convert_to_liberal(obj):
    if isinstance(obj, basestring):
        return obj
    elif isinstance(obj, int):
        return str(obj)
    elif isinstance(obj, datetime.datetime):
        return PyRSS2Gen._format_date(obj)
    else:
        d = {}
        for k, v in obj.__dict__.items():
            if v is None:
                continue
            if k == "element_attrs":
                d.update(v)
            elif k in ("categories", "days", "hours", "author",
                       "comments", "source"):
                # feedparser doesn't handle these
                continue
            elif k == "guid" and not isinstance(v, str):
                d[k] = v.guid
            else:
                if k == "pubDate":
                    k = "date"
                d[k] = _convert_to_liberal(v)
        return d
        

def to_liberal(rss):
    d = {"encoding": "iso-8859-1"}  # a bit of a hack
    channel = d["channel"] = {}
    items = rss.__dict__.items() # enforce an (arbitrary) order
    items.sort()                 # (feedparser result depends on the
    for k, v in items:           # order of the elements.)
        if v is None:
            continue
        if k in ("categories", "docs", "generator", "cloud", "ttl",
                 "image", "rating", "textInput", "skipDays", "skipHours"):
            # feedparser doesn't handle these
            pass
        elif k != "items":
            # Why the changes?
            if k == "copyright":
                k = "rights"
            elif k == "lastBuildDate":
                k = "date"
            elif k in ("webMaster", "managingEditor"):
                k = "creator"   # order dependent!
            elif k in ("pubDate", "lastBuildDate"):
                if "date" in channel:
                    # lastBuildDate has priority
                    if k == "pubDate":
                        continue
                k = "date"  # also order dependent
            channel[k] = _convert_to_liberal(v)
        
    items = [_convert_to_liberal(item) for item in rss.items]
    d["items"] = items

    return d

s = rss.to_xml()
import cStringIO as StringIO
f = StringIO.StringIO(s)
result = feedparser.parse(f)
##print result
##print "=========="
##print to_liberal(rss)

result2 = to_liberal(rss)
assert result == result2

execfile("example.py")

# Check a few things new to 1.0

def EQ(x, y):
    if not (x == y):
        raise AssertionError( (x, y) )

class RecordingHandler:
    def __init__(self):
        self.events = []
    def startElement(self, tag, d):
        self.events.append( ("SE", tag, d) )
    def characters(self, text):
        self.events.append( ("C", text) )
    def endElement(self, tag):
        self.events.append( ("EE", tag) )

def publish_it(obj):
    h = RecordingHandler()
    obj.publish(h)
    return h.events

obj = PyRSS2Gen.Enclosure("http://example.com", 5, "text/plain")
EQ(publish_it(obj), [("SE", "enclosure", {"url": "http://example.com",
                                          "length": "5",
                                          "type": "text/plain"}),
                     ("EE", "enclosure"),
                     ])

obj = PyRSS2Gen.Guid("ABCDEF", False)
EQ(publish_it(obj), [("SE", "guid", {"isPermaLink": "false"}),
                     ("C", "ABCDEF"),
                     ("EE", "guid"),
                     ])
