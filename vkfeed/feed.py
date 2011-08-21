"""Generates an RSS feed."""

import httplib
import logging
import re

from google.appengine.ext import webapp

from vkfeed.core import Error
import vkfeed.util


class Feed(webapp.RequestHandler):
    """Generates an RSS feed."""


    def get(self, profile_name):
        """Processes the request."""

        logging.info("Requested feed for '%s'.", profile_name)

        url = "http://vk.com/" + profile_name

        try:
            profile_page = vkfeed.util.fetch_url(url)
            self.__parse_wall_page(profile_page)
        except Error, e:
            logging.error("Unable to generate a feed for '%s': %s.", url, e)

            self.error(httplib.BAD_GATEWAY)
            self.response.out.write(vkfeed.util.render_template("feed_error.html", {
                "feed_source": url,
                "error":       e
            }))
        else:
            self.response.out.write("OK")


    def __parse_wall_page(self, profile_page):
        # Get wall HTML -->
        match = re.search(r"""
            <div
                (?:\s+[^>]+){0,1}
                \s+id\s*=\s*['"]page_wall_posts['"]
                (?:\s+[^>]*){0,1}
            >
                (?P<wall_html>.*)
            <a
                (?:\s+[^>]+){0,1}
                \s+id\s*=\s*['"]wall_more_link['"]
                (?:\s+[^>]*){0,1}
            >
        """, profile_page, re.DOTALL | re.IGNORECASE | re.VERBOSE)

        if not match:
            raise Error("GGGGGGG")
            #raise Error("The server returned a page with unexpected content. Either you specified an incorrect name for the profile or the code changed.

        wall_html = match.group("wall_html")
        # Get wall HTML <--

        # Get wall posts HTML
        posts_html = self.__get_posts_html(wall_html)
        self.__parse_posts_html(posts_html)

#        post_regex = re.compile(r"""
#            <div
#                (\s+[^>]+){0,1}
#                \s+id\s*=\s*['"]post-(\d+_\d+)['"]
#                (\s+[^>]*){0,1}
#            >
#                (.*)
#        """, re.DOTALL | re.IGNORECASE | re.VERBOSE)
#
#        posts = []
#        for match in post_regex.finditer(wall_html):
#            posts.append((match.group(2), match.group(4)))
#        raise Error(posts)


    def __get_posts_html(self, wall_html):
        """Obtains a list of post HTML from wall HTML."""

        posts_html = re.split(r"""
            <div
                (?:\s+[^>]+){0,1}
                \s+id\s*=\s*['"]post-(\d+_\d+)['"]
                (?:\s+[^>]*){0,1}
            >
        """, wall_html, flags = re.DOTALL | re.IGNORECASE | re.VERBOSE)[1:]

        if not posts_html:
            match = re.search(r"""
                <div
                    (?:\s+[^>]+){0,1}
                    \s+id\s*=\s*['"]page_no_wall['"]
                    (?:\s+[^>]*){0,1}
                >
            """, wall_html, re.DOTALL | re.IGNORECASE | re.VERBOSE)

            if match:
                return
            else:
                raise Error("GGGGGGGGG")

# TODO: check size
        posts_ids_html = []
        for i in xrange(len(posts_html) // 2):
            posts_ids_html.append(( posts_html[i], posts_html[i + 1] ))

        return posts_ids_html


    def __parse_posts_html(self, posts_html):
        post_regex = re.compile(r"""
            <table
                (?:\s+[^>]+){0,1}
                \s+class\s*=\s*['"]post_table['"]
                (?:\s+[^>]*){0,1}
            >
            .*
            <td
                (?:\s+[^>]+){0,1}
                \s+class\s*=\s*['"]info['"]
                (?:\s+[^>]*){0,1}
            >
            .*
            <div
                (?:\s+[^>]+){0,1}
                \s+class\s*=\s*['"]text['"]
                (?:\s+[^>]*){0,1}
            >
            .*
            (
                <div
                    (?:\s+[^>]+){0,1}
                    \s+class\s*=\s*['"]wall_post_text['"]
                    (?:\s+[^>]*){0,1}
                >
                .*
            )
            </div>
            .*
            <div class="like_wrap fl_r"
        """, re.DOTALL | re.IGNORECASE | re.VERBOSE)

        posts = []
        for post_id, post_html in posts_html:
#            raise Error(post_html)
            raise Error(post_regex.search(post_html).group(1))

