#! /usr/bin/env python
# encoding: utf-8
#
# wscript for building and installing termsize

from __future__ import print_function

import os
import subprocess
import shutil
import re
import time

from waflib import Logs, Options, TaskGen, Context, Utils
from waftoolchainflags import WafToolchainFlags

APPNAME='termsize'
VERSION='0-dev'

# these variables are mandatory ('/' are converted automatically)
srcdir = '.'
blddir = 'build'

def git_ver(self):
    bld = self.generator.bld
    header = self.outputs[0].abspath()
    if os.access('./version.h', os.R_OK):
        header = os.path.join(os.getcwd(), out, "version.h")
        shutil.copy('./version.h', header)
        data = open(header).read()
        m = re.match(r'^#define GIT_VERSION "([^"]*)"$', data)
        if m != None:
            self.ver = m.group(1)
            Logs.pprint('BLUE', "tarball from git revision " + self.ver)
        else:
            self.ver = "tarball"
        return

    if bld.srcnode.find_node('.git'):
        self.ver = bld.cmd_and_log("LANG= git rev-parse HEAD", quiet=Context.BOTH).splitlines()[0]
        if bld.cmd_and_log("LANG= git diff-index --name-only HEAD", quiet=Context.BOTH).splitlines():
            self.ver += "-dirty"

        Logs.pprint('BLUE', "git revision " + self.ver)
    else:
        self.ver = "unknown"

    fi = open(header, 'w')
    if self.ver != "unknown":
        fi.write('#define GIT_VERSION "%s"\n' % self.ver)
    fi.close()

def display_msg(conf, msg="", status = None, color = None):
    if status is None:
        Logs.pprint('NORMAL', msg)
        return
    if isinstance(status,bool):
        if status:
            status = "yes"
            if not color:
                color = 'GREEN'
        else:
            status = "no"
            if not color:
                color = 'YELLOW'
    elif not isinstance(status,str):
        status = repr(status)
    conf.msg(msg, status, color=color)
    #Logs.pprint(msg, status, color)

def display_raw_text(conf, text, color = 'NORMAL'):
    Logs.pprint(color, text, sep = '')

def display_line(conf, text, color = 'NORMAL'):
    Logs.pprint(color, text, sep = os.linesep)

def options(opt):
    # options provided by the modules
    opt.load('compiler_c')
    opt.load('wafautooptions')

    opt.add_auto_option(
        'devmode',
        help='Enable devmode', # enable warnings and treat them as errors
        conf_dest='BUILD_DEVMODE',
        default=False,
    )

    opt.add_auto_option(
        'debug',
        help='Enable debug symbols',
        conf_dest='BUILD_DEBUG',
        default=False,
    )

def configure(conf):
    conf.load('compiler_c')
    conf.load('wafautooptions')

    flags = WafToolchainFlags(conf)

    conf.define('TERMSIZE_VERSION', VERSION)
    conf.define('HAVE_GITVERSION_H', 1)
    conf.define('BUILD_TIMESTAMP', time.ctime())
    conf.write_config_header('config.h')

    flags.add_c('-std=gnu99')
    if conf.env['BUILD_DEVMODE']:
        flags.add_c(['-Wall', '-Wextra'])
        #flags.add_c('-Wpedantic')
        flags.add_c('-Werror')
        flags.add_c(['-Wno-variadic-macros', '-Wno-gnu-zero-variadic-macro-arguments'])

        # https://wiki.gentoo.org/wiki/Modern_C_porting
        if conf.env['CC'] == 'clang':
            flags.add_c('-Wno-unknown-argumemt')
            flags.add_c('-Werror=implicit-function-declaration')
            flags.add_c('-Werror=incompatible-function-pointer-types')
            flags.add_c('-Werror=deprecated-non-prototype')
            flags.add_c('-Werror=strict-prototypes')
            if int(conf.env['CC_VERSION'][0]) < 16:
                flags.add_c('-Werror=implicit-int')
        else:
            flags.add_c('-Wno-unknown-warning-option')
            flags.add_c('-Werror=implicit-function-declaration')
            flags.add_c('-Werror=implicit-int')
            flags.add_c('-Werror=incompatible-pointer-types')
            flags.add_c('-Werror=strict-prototypes')
    if conf.env['BUILD_DEBUG']:
        flags.add_c(['-O0', '-g', '-fno-omit-frame-pointer'])
        flags.add_link('-g')

    flags.flush()

    gitrev = None
    if os.access('gitversion.h', os.R_OK):
        data = file('gitversion.h').read()
        m = re.match(r'^#define GIT_VERSION "([^"]*)"$', data)
        if m != None:
            gitrev = m.group(1)

    print()
    display_msg(conf, "==================")
    version_msg = APPNAME + "-" + VERSION
    if gitrev:
        version_msg += " exported from " + gitrev
    else:
        version_msg += " git revision will checked and eventually updated during build"
    print(version_msg)
    print()

    display_msg(conf, "Install prefix", conf.env['PREFIX'], 'CYAN')
    display_msg(conf, "Compiler", conf.env['CC'][0], 'CYAN')
    conf.summarize_auto_options()
    flags.print()
    print()

def build(bld):
    bin_dir = bld.env['BINDIR']
    share_dir = bld.options.destdir + bld.env['PREFIX'] + '/share/' + APPNAME
    #print(bin_dir)
    #print(share_dir)

    bld(rule=git_ver,
        target='gitversion.h',
        update_outputs=True,
        always=True,
        ext_out=['.h'])

    # config.h, gitverson.h include path; public headers include path
    includes = [bld.path.get_bld()]

    prog = bld(features=['c', 'cprogram'])
    prog.source = [
        'termsize.c',
        ]
    prog.includes = includes
    prog.target = 'termsize'
    prog.defines = ["HAVE_CONFIG_H"]
