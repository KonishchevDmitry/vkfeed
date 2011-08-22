# -*- coding: utf-8 -*-

"""Parses a vk.com wall page."""

import logging
import re

from vkfeed.core import Error
from vkfeed.html_parser import HTMLPageParser


class ParseError(Error):
    """Raised if we are unable to parse a gotten data."""

    def __init__(self, *args, **kwargs):
        Error.__init__(self, *args, **kwargs)



class WallPageParser(HTMLPageParser):
    """Parses a vk.com wall page."""

    __data = None
    """The page data."""

    __private_data = None
    """Various state data."""


    __show_more_regex = re.compile(r"<a" + HTMLPageParser.tag_attrs_regex + ur">показать полностью\.*</a>", re.IGNORECASE)
    """Regular expression for "Show more..." link."""


    def __init__(self):
        HTMLPageParser.__init__(self)


    def handle_root_data(self, tag, data):
        """Handles data inside of the root of the document."""


    def handle_root_new_tag(self, tag, attrs, empty):
        """Handles a tag inside of the root of the document."""

        if tag["name"] == "html":
            tag["new_tag_handler"] = self.__handle_html_new_tag


    def handle_root_tag_end(self, tag):
        """Handles end of the root of the document."""


    def parse(self, html):
        """Parses the specified HTML."""

        self.__data = {}
        self.__private_data = {}
        HTMLPageParser.parse(self, html)

        if "user" not in self.__data:
            raise ParseError("Unable to find the user name.")

        if "posts" not in self.__data:
            raise ParseError("Unable to find the wall.")

        if not self.__data["posts"] and not self.__private_data.get("wall_is_empty"):
            raise ParseError("Unable to find wall posts.")

        return self.__data



    def __handle_html_new_tag(self, tag, attrs, empty):
        """Handles a tag inside of <html>."""

        if tag["name"] == "head":
            tag["new_tag_handler"] = self.__handle_head_new_tag
        elif tag["name"] == "body":
            tag["new_tag_handler"] = self.__handle_body_new_tag


    def __handle_head_new_tag(self, tag, attrs, empty):
        """Handles a tag inside of <head>."""

        if tag["name"] == "title":
            tag["data_handler"] = self.__handle_title_data


    def __handle_title_data(self, tag, data):
        """Handles data inside of <title>."""

        data = data.strip()
        if not data:
            raise ParseError("The title is empty.")

        self.__data["user"] = data



    def __handle_body_new_tag(self, tag, attrs, empty):
        """Handles a tag inside of <body>."""

        if tag["name"] == "div" and attrs.get("id") == "page_wall_posts":
            tag["new_tag_handler"] = self.__handle_page_wall_posts
            self.__data["posts"] = []
        else:
            if "posts" not in self.__data:
                tag["new_tag_handler"] = self.__handle_body_new_tag


    def __handle_page_wall_posts(self, tag, attrs, empty):
        """Handles a tag inside of <div id="page_wall_posts">."""

        if (
            tag["name"] == "div" and
            attrs.get("id", "").startswith("post") and
            len(attrs["id"]) > len("post") and
            self.__has_class(attrs, "post")
        ):
            if empty:
                raise ParseError("Post '%s' div tag is empty.", attrs["id"])

            tag["new_tag_handler"] = self.__handle_post
            tag["end_tag_handler"] = self.__handle_post_end

            self.__add_post( attrs["id"][len("post"):] )
        elif tag["name"] == "div" and attrs.get("id") == "page_no_wall":
            self.__private_data["wall_is_empty"] = True
        else:
            tag["new_tag_handler"] = self.__handle_page_wall_posts


    def __handle_post(self, tag, attrs, empty):
        """Handles a tag inside of <div id="post...">."""

        if tag["name"] == "table" and self.__has_class(attrs, "post_table"):
            tag["new_tag_handler"] = self.__handle_post_table
        else:
            if not self.__get_cur_post()["text"]:
                tag["new_tag_handler"] = self.__handle_post


    def __handle_post_table(self, tag, attrs, empty):
        """Handles a tag inside of <table class="post_table">."""

        if tag["name"] == "tr":
            tag["new_tag_handler"] = self.__handle_post_table_row


    def __handle_post_table_row(self, tag, attrs, empty):
        """Handles a tag inside of <table class="post_table"><tr>."""

        if tag["name"] == "td" and self.__has_class(attrs, "info"):
            tag["new_tag_handler"] = self.__handle_post_table_row_info


    def __handle_post_table_row_info(self, tag, attrs, empty):
        """Handles a tag inside of <table class="post_table"><tr><td class="info">."""

        if tag["name"] == "div" and self.__has_class(attrs, "text"):
            tag["new_tag_handler"] = self.__handle_post_text
        else:
            tag["new_tag_handler"] = self.__handle_post_table_row_info


    def __handle_post_text(self, tag, attrs, empty):
        """Handles a tag inside of <table class="post_table"><tr><td class="info"><div class="text">."""

        if tag["name"] == "div":
            self.__handle_post_data_container(tag, attrs, empty)


    def __handle_post_data_container(self, tag, attrs, empty):
        """Handles a tag inside of post data tag."""

        self.__get_cur_post()["text"] += self.__escape_tag(tag["name"], attrs, empty)
        tag["new_tag_handler"] = self.__handle_post_data_container
        tag["data_handler"] = self.__handle_post_data
        if not empty:
            tag["end_tag_handler"] = self.__handle_post_data_end


    def __handle_post_data(self, tag, data):
        """Handles data inside of post data tag."""

        self.__get_cur_post()["text"] += data


    def __handle_post_data_end(self, tag):
        """Handles end of a post data tag."""

        self.__get_cur_post()["text"] += "</%s>" % tag["name"]


    def __handle_post_end(self, tag):
        """Handles end of <div id="post...">."""

        cur_post = self.__get_cur_post()

        text = cur_post["text"]
        text = self.__show_more_regex.sub("", text)
        cur_post["text"] = text.strip()



    def __add_post(self, post_id):
        """Adds a new post to the wall."""

        self.__data["posts"].append({
            "id":   post_id,
            "text": "",
        })


        # TODO
    def __escape_tag(self, tag_name, attrs, empty):
        """Escapes the specified tag and its attributes."""

        data = "<" + tag_name

        for attr, value in attrs.iteritems():
            if (
                tag_name == "img" and attr == "src" or
                tag_name == "a" and attr == "href"
            ):
                if not re.match("[a-z]+://", value):
                    value = "http://vk.com/" + value
                data += " " + attr + "='" + value + "'"

        return data + "%s>" % ("/" if empty else "")

        return "<%s%s>" % (tag_name, "/" if empty else "")


    def __get_cur_post(self):
        """Returns current post."""

        return self.__data["posts"][-1]


    def __has_class(self, attrs, class_name):
        """
        Checks whether a tag with the specified attributes has the specified
        class.
        """

        return class_name in attrs.get("class", "").split(" ")

