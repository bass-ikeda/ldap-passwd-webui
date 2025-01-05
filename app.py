#!/usr/bin/env python3

import bottle
from bottle import get, post, static_file, request, route, template
from bottle import SimpleTemplate
from configparser import ConfigParser
from ldap3 import Connection, Server
from ldap3 import SIMPLE, SUBTREE
from ldap3.core.exceptions import   \
    LDAPBindError,                  \
    LDAPConstraintViolationResult,  \
    LDAPInvalidCredentialsResult,   \
    LDAPUserNameIsMandatoryError,   \
    LDAPSocketOpenError,            \
    LDAPExceptionError
import logging
import logging.handlers
import gettext
import os
from os import environ, path
import sys
from subprocess import Popen, PIPE
import shlex

BASE_DIR = path.dirname(__file__)
VERSION = '3.0.0-it'
environ['DEBUG'] = ''   # set '1' for DEBUG


#--------------------------------------
# CUSTOM packages

sys.path.append(BASE_DIR)
from lib.lpw_i18n import languages_list, lang_decide


#--------------------------------------
# for bottle framework

@get('/')
def get_index():
    lang = lang_decide(request, CONF)
    i18n_set_lang(lang)
    return index_tpl(lang=lang)


@post('/')
def post_index():
    form = request.forms.getunicode
    lang = lang_decide(request, CONF)
    i18n_set_lang(lang)

    def error(msg):
        messages = []
        for s in msg.rstrip("\n").split("\n"):
            messages.append(('error', s))
        return index_tpl(username=form('username'), lang=lang, alerts=messages)

    if form('new-password') != form('confirm-password'):
        return error(_("Password doesn't match the confirmation!"))

    try:
        passwd_length_min = int(CONF['html']['passwd_length_min'])
    except KeyError:
        passwd_length_min = 8
    except ValueError as e:
        admin_msg = "invalid passwd_length_min, CALL administrator please."
        LOG.error("%s : %s" % (admin_msg, str(e)))
        return error(admin_msg)

    if len(form('new-password')) < int(passwd_length_min):
        return error(_("Password must be at least ")    \
                     + str(passwd_length_min)           \
                     + _(" characters long!")
        )

    # call hook: password_policy
    errors = hook_password_policy(
        form('username'), form('old-password'),
        form('new-password'), form('confirm-password')
    )
    if len(errors):
        return error(errors)

    try:
        change_passwords(
            form('username'), form('old-password'), form('new-password')
        )
    except Error as e:
        LOG.warning(
            _("Unsuccessful attempt to change password for %s: %s")
            % (form('username'), e)
        )
        return error(str(e))

    LOG.info("Password successfully changed for: %s" % form('username'))

    return index_tpl(lang=lang, alerts=[
        ('success', _("Password has been changed"))
    ])


@route('/static/<filename>', name='static')
def serve_static(filename):
    return static_file(filename, root=path.join(BASE_DIR, 'static'))


def index_tpl(lang=None, **kwargs):
    tpl_name = 'index'

    tpl_path = tpl_name
    locale_lang = languages_list(localedir=LOCALE_DIR, languages=[lang],
                                 get_path=True, get_abspath=False)
    if len(locale_lang) > 0:
        tpl_path = path.join(locale_lang[0], tpl_name)

    if not path.isfile(tpl_path + '.tpl'):
        tpl_path = tpl_name

    return template(tpl_path, lang=lang, **kwargs)


#--------------------------------------
# for LDAP access, and modify passwords

def connect_ldap(conf, **kwargs):
    server = Server(host=conf['host'],
                    port=conf.getint('port', None),
                    use_ssl=conf.getboolean('use_ssl', False),
                    connect_timeout=5)

    return Connection(server, raise_exceptions=True, **kwargs)


def change_passwords(username, old_pass, new_pass):
    changed = []

    for key in (key for key in CONF.sections()
                if key == 'ldap' or key.startswith('ldap:')):

        LOG.debug("Changing password in %s for %s" % (key, username))
        try:
            change_password(CONF[key], username, old_pass, new_pass)
            changed.append(key)
        except Error as e:
            for key in reversed(changed):
                LOG.info(
                    "Reverting password change in %s for %s"
                    % (key, username)
                )
                try:
                    change_password(CONF[key], username, new_pass, old_pass)
                except Error as e2:
                    LOG.error('{}: {!s}'.format(e.__class__.__name__, e2))
            raise e


def change_password(conf, *args):
    try:
        if conf.get('type') == 'ad':
            change_password_ad(conf, *args)
        else:
            change_password_ldap(conf, *args)

    except (
            LDAPBindError,
            LDAPInvalidCredentialsResult,
            LDAPUserNameIsMandatoryError
            ):
        raise Error(_('Username or password is incorrect!'))

    except LDAPConstraintViolationResult as e:
        # Extract useful part of the error message (for Samba 4 / AD).
        msg = e.message.split('check_password_restrictions: ')[-1].capitalize()
        raise Error(msg)

    except LDAPSocketOpenError as e:
        LOG.error('{}: {!s}'.format(e.__class__.__name__, e))
        raise Error(_('Unable to connect to the remote server.'))

    except LDAPExceptionError as e:
        LOG.error('{}: {!s}'.format(e.__class__.__name__, e))
        raise Error(_(
            'Encountered an unexpected error while communicating with the remote server.'
        ))

    # call hook: password_change
    errors = hook_password_change(*args)
    if len(errors):
        raise Error(_(errors))


def change_password_ldap(conf, username, old_pass, new_pass):
    # use BIND DN, instead of Anonymous Bind
    # 1. build BIND DN
    binddn = conf['search_filter'].replace('{uid}', username)   \
             + ',' + conf['base']

    # 2. connect with BIND DN
    with connect_ldap(conf, authentication=SIMPLE,
                      user=binddn, password=old_pass) as c:
        user_dn = find_user_dn(conf, c, username)

    # Note: raises LDAPUserNameIsMandatoryError when user_dn is None.
    with connect_ldap(conf, authentication=SIMPLE,
                      user=user_dn, password=old_pass) as c:
        c.bind()
        c.extend.standard.modify_password(user_dn, old_pass, new_pass)


def change_password_ad(conf, username, old_pass, new_pass):
    user = username + '@' + conf['ad_domain']

    with connect_ldap(conf, authentication=SIMPLE,
                      user=user, password=old_pass) as c:
        c.bind()
        user_dn = find_user_dn(conf, c, username)
        c.extend.microsoft.modify_password(user_dn, new_pass, old_pass)


def find_user_dn(conf, conn, uid):
    search_filter = conf['search_filter'].replace('{uid}', uid)
    conn.search(conf['base'], "(%s)" % search_filter, SUBTREE)

    return conn.response[0]['dn'] if conn.response else None


#--------------------------------------
# for config

def read_config():
    config = ConfigParser()
    config.read([
        path.join(BASE_DIR, 'settings.ini'),
        os.getenv('CONF_FILE', '')
    ])

    return config


#--------------------------------------
# for i18n

def i18n_set_lang(language):
    translate = gettext.translation(
        'app.py', LOCALE_DIR, fallback=True, languages=[language]
    )
    _ = translate.gettext

    translate.install()


#--------------------------------------
# for hooks

def hook_password_policy(username, old_pass, new_pass, confirm_pass):
    cmd = CONF['hook']['program_password_policy']
    return call_hook(cmd, username, old_pass, new_pass, confirm_pass)


def hook_password_change(username, old_pass, new_pass):
    cmd = CONF['hook']['program_password_change']
    return call_hook(cmd, username, old_pass, new_pass, new_pass)


def call_hook(cmd, username, old_pass, new_pass, confirm_pass):
    # check if `cmd` is executable
    args = shlex.split(cmd)
    if (not os.access(args[0], os.X_OK)):
        admin_msg = args[0] + " is NOT executable, CALL administrator please."
        LOG.error(admin_msg)
        return admin_msg

    # open pipelines and join the `cmd` to them
    p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)

    (child_stdin,
     child_stdout,
     child_stderr) = (p.stdin, p.stdout, p.stderr)

    # write data into STDIN of the `cmd`
    # data: 4 lines
    #
    #   username\n
    #   old_pass\n
    #   new_pass\n
    #   confirm_pass\n
    #
    str_input = "\n".join([username, old_pass, new_pass, confirm_pass]) + "\n"
    child_stdin.write(str_input.encode())
    child_stdin.close()

    # get responses
    stdout = child_stdout.read().decode()
    stderr = child_stderr.read().decode()

    # LOG messages of STDOUT, as DEBUG
    if len(stdout):
        for s in stdout.rstrip("\n").split("\n"):
            LOG.debug(username + " / " + s)

    # LOG messages of STDERR, as ERROR
    stderr_i18n = []
    if len(stderr):
        for s in stderr.rstrip("\n").split("\n"):
            LOG.warning(username + " / " + s)

            # here translate error messages
            stderr_i18n.append(_(s))

    # return ERRORS, as string
    # or empty string if all successful and NO errors
    return "\n".join(stderr_i18n)


#--------------------------------------
# for Exception

class Error(Exception):
    pass


#----------------------------------------------------------------------
# Do IT !

# Set up logging.
LOG = logging.getLogger(__name__)

log_format = '%(asctime)s %(levelname)s: %(message)s'
logging.basicConfig(format=log_format, encoding='utf-8')

syslog_handler = logging.handlers.SysLogHandler(address = '/dev/log')
LOG.addHandler(syslog_handler)

LOG.setLevel(logging.INFO)

if environ.get('DEBUG'):
    bottle.debug(True)
    LOG.setLevel(logging.DEBUG)

# config
CONF = read_config()

# Set up bottle
bottle.TEMPLATE_PATH = [BASE_DIR]

# Set up i18n with gettext
LOCALE_DIR = './locale/'

# Set default attributes to pass into templates.
SimpleTemplate.defaults = dict(CONF['html'])
SimpleTemplate.defaults['url'] = bottle.url


LOG.info("Starting ldap-passwd-webui %s" % VERSION)

# Run bottle internal server when invoked directly (mainly for development).
if __name__ == '__main__':
    bottle.run(**CONF['server'])
# Run bottle in application mode (in production under uWSGI server).
else:
    application = bottle.default_app()
