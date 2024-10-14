import glob
import os
import re
from bottle import request
from gettext import _expand_lang


def languages_list(localedir=None,
                   languages=[], get_path=False, get_abspath=False):

    # Get some reasonable defaults for arguments that were not supplied
    if localedir is None:
        localedir = _default_localedir

    # get list of existing language directory
    langdir_all = []
    for d in glob.glob(os.path.join(localedir, './*')):
        if os.path.isdir(d):
            langdir_all.append(os.path.basename(d))

    # if languages are set,
    # ->select matching languages
    lang_candidates = []
    if len(languages) == 0:
        lang_candidates = langdir_all
    for l in languages:
        # normalize and expand the languages
        for nel in _expand_lang(l):
            if nel in lang_candidates:
                continue
            lang_candidates.append(nel)

    # select matching languages
    result = []
    prefix = ''
    if get_path:
        prefix = localedir
    if get_abspath:
        prefix = os.path.abspath(localedir)
    for lang in langdir_all:
        if lang not in lang_candidates:
            continue
        result.append(os.path.join(prefix, lang))

    return result


def lang_decide(request=None, conf=None):

    if ((request is None) or (conf is None)):
        return ''

    lang = None

    # 1. GET request: query string `?lang=(Language)`
    if lang is None:
        lang = request.GET.getunicode('lang', default=None)

    # 2. POST request: header value `lang: (Language)`
    if lang is None:
        lang = request.POST.getunicode('lang', default=None)

    # 3. Cookie value:
    if lang is None:
        lang = request.cookies.get('lang', default=None)

    # 4. settings.ini: `default_lang = (Language)` in `[server]` section
    if lang is None:
        lang = conf['i18n'].get('default_language')

    # 5.　request header: `Accept-Language: fr-FR,fr`
    if lang is None:
        accept_langs = request.headers.get('accept-language', default='')
        if accept_langs is not None:
            lang_list = re.split(r'\W+', accept_langs.replace('-', '_'))
            lang = lang_list[0]

    # 6. (default) ->lang=''
    if lang is None:
        return ''

    return lang
