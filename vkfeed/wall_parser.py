"""Parses a vk.com wall page."""

import logging

from vkfeed.core import Error
from vkfeed.html_parser import HTMLPageParser


class WallPageParser(HTMLPageParser):
    """Parses a vk.com wall page."""

    __data = None
    """The wall data."""

    __private_data = None
    """Various state data."""


    def __init__(self):
        HTMLPageParser.__init__(self)


    def handle_root_data(self, tag, data):
        """Handles data inside of the root of the document."""


    def handle_root_tag_end(self, tag):
        """Handles end of a tag inside of the root of the document."""


    def handle_root_tag_start(self, tag, attrs, empty):
        """Handles start of a tag inside of the root of the document."""

        if tag["name"] == "html":
            tag["start_tag_handler"] = self.__handle_html_tag_start


    def parse(self, html):
        """Parses the specified HTML."""

        self.__data = {}
        self.__private_data = {}
        HTMLPageParser.parse(self, html)

        if "title" not in self.__data:
            raise Error("Unable to find the page title.")

        if "wall" not in self.__data:
            raise Error("Unable to find the wall.")

        if not self.__data["wall"] and not self.__private_data.get("wall_is_empty"):
            raise Error("Unable to find the wall posts.")

        return self.__data



    def __handle_html_tag_start(self, tag, attrs, empty):
        """Handles start of a tag inside of <html>."""

        if tag["name"] == "head":
            tag["start_tag_handler"] = self.__handle_head_tag_start
        elif tag["name"] == "body":
            tag["start_tag_handler"] = self.__handle_body_tag_start


    def __handle_head_tag_start(self, tag, attrs, empty):
        """Handles start of a tag inside of <head>."""

        if tag["name"] == "title":
            tag["data_handler"] = self.__handle_title_data


    def __handle_title_data(self, tag, data):
        """Handles data inside of <title>."""

        data = data.strip()
        if not data:
            raise Error("The title is empty.")

        self.__data["title"] = data



    def __handle_body_tag_start(self, tag, attrs, empty):
        """Handles start of a tag inside of <body>."""

        if tag["name"] == "div" and attrs.get("id") == "page_wall_posts":
            tag["start_tag_handler"] = self.__handle_page_wall_posts
            self.__data["wall"] = []
        else:
            if "wall" not in self.__data:
                tag["start_tag_handler"] = self.__handle_body_tag_start


    def __handle_page_wall_posts(self, tag, attrs, empty):
        """Handles start of a tag inside of <div id="page_wall_posts">."""

        if tag["name"] == "div" and attrs.get("id") == "page_no_wall":
            self.__private_data["wall_is_empty"] = True

