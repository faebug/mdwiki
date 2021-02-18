# -*- coding: utf-8  -*-

from pywikibot import family

# mdWiki.org

class Family(family.Family):

    name = 'mdwiki' # Set the family name; this should be the same as in the filename.
    langs = {
        'en': 'mdwiki.org', # Put the hostname here.
    }

    def scriptpath(self, code):
        return '/w' # The relative path of index.php, api.php : look at your wiki address.
