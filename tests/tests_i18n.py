#!/usr/bin/python3

import unittest
import sys
sys.path.append("..")
from lib.lpw_i18n import *


class TestLibI18n(unittest.TestCase):

    def test_languages_list_get_list(self):
        self.assertEqual(
            languages_list(localedir='../locale/'),
            ['ja_JP'],
            msg="languages_list returns a list of Locale directories."
        )

    def test_languages_list_get_empty_list_for_bad_localedir(self):
        self.assertEqual(
            languages_list(localedir='../NotExist/'),
            [],
            msg="languages_list returns an Empty list for bad localedir."
        )

    def test_languages_list_get_list_getpath_false(self):
        self.assertEqual(
            languages_list(localedir='../locale/', get_path=False),
            ['ja_JP'],
            msg="languages_list returns names of Locale directories."
        )

    def test_languages_list_get_list_getpath_true(self):
        dirs_lang = ['ja_JP']
        dir_locale = '../locale/'

        expected = []
        for d in dirs_lang:
            expected.append(os.path.join(dir_locale, d))

        self.assertEqual(
            languages_list(localedir=dir_locale, get_path=True),
            expected,
            msg="languages_list returns pathnames of Locale directories."
        )

    def test_languages_list_get_list_abspath_false(self):
        self.assertEqual(
            languages_list(localedir='../locale/', get_abspath=False),
            ['ja_JP'],
            msg="languages_list returns names of Locale directories."
        )

    def test_languages_list_get_list_abspath_true(self):
        dirs_lang = ['ja_JP']
        dir_locale = '../locale/'

        expected = []
        for d in dirs_lang:
            expected.append(os.path.realpath(os.path.join(dir_locale, d)))

        self.assertEqual(
            languages_list(localedir=dir_locale, get_abspath=True),
            expected,
            msg="languages_list returns Absolute names of Locale directories."
        )

    def test_languages_list_languages(self):
        self.assertEqual(
            languages_list(localedir='../locale/', languages=['ja']),
            ['ja_JP'],
            msg="languages_list returns a list of ja language"
        )

    def test_languages_list_languages_bad_lang(self):
        self.assertEqual(
            languages_list(localedir='../locale/', languages=['xx']),
            [],
            msg="languages_list returns a Empty list for a bad language"
        )


if __name__ == '__main__':
    unittest.main()
