#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests vk.com wall parser."""

import unittest

from vkfeed.wall_parser import WallPageParser


class TestWallParser(unittest.TestCase):
    """Tests vk.com wall parser."""

    def setUp(self):
        self.__parser = WallPageParser()


    def test_empty_wall(self):
        """Testing parsing of empty wall."""

        html = open("wall_parser/empty_wall.html").read().decode("cp1251")

        etalon = {
            "title":     u"Дмитрий Конищев",
            "wall":      [],
            "wall_size": 0,
        }

        clear_run_data = self.__normalize_data(self.__parser.parse(html))
        self.assertEqual(etalon, clear_run_data)

        dirty_run_data = self.__normalize_data(self.__parser.parse(html))
        self.assertEqual(etalon, clear_run_data)
        self.assertEqual(etalon, dirty_run_data)


    def test_filled_wall(self):
        """Testing parsing of filled wall."""

        # TODO


    def __normalize_data(self, data):
        """Removes fields that don't exist in the etalon."""

        if "wall" in data:
            data["wall_size"] = len(data["wall"])
            data["wall"] = []

        return data



if __name__ == '__main__':
    # TODO
    import logging
    logging.getLogger().setLevel(logging.DEBUG)
    unittest.main()

