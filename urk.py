#!/usr/bin/python -O

import imp
import os
import sys
import traceback

sys.modules['urk'] = sys.modules[__name__]

#add ~/.urk and path (normally where urk.py is located) to sys.path
urkpath = os.path.dirname(__file__)
def path(filename=""):
    if filename:
        return os.path.join(urkpath, filename)
    else:
        return urkpath

if 'URK_PROFILE' in os.environ:
    userpath = os.environ['URK_PROFILE']
    if not os.access(userpath,os.F_OK):
        os.mkdir(userpath, 0700)
    if not os.access(os.path.join(userpath,'scripts'),os.F_OK):
        os.mkdir(os.path.join(userpath,'scripts'), 0700)
elif os.access(path('profile'),os.F_OK) or os.path.expanduser("~") == "~":
    userpath = path('profile')
    if not os.access(userpath,os.F_OK):
        os.mkdir(userpath)
    if not os.access(os.path.join(userpath,'scripts'),os.F_OK):
        os.mkdir(os.path.join(userpath,'scripts'))
else:
    userpath = os.path.join(os.path.expanduser("~"), ".urk")
    if not os.access(userpath,os.F_OK):
        os.mkdir(userpath, 0700)
    if not os.access(os.path.join(userpath,'scripts'),os.F_OK):
        os.mkdir(os.path.join(userpath,'scripts'), 0700)

platforms = ['gtk', 'stdio']

def test_platform(platform, verbose=False):
    try:
        f = open(os.path.join(path('platform'), platform, 'check.py'), 'U')
    except:
        if verbose:
            traceback.print_exc()
        return False
    try:
        exec f.read()
        return True
    except:
        if verbose:
            traceback.print_exc()
        return False
    finally:
        f.close()

if 'URK_PLATFORM' in os.environ:
    platform = os.environ['URK_PLATFORM']
    if not test_platform(platform, verbose=True):
        print("Cannot use forced platform '%s'" % platform)
        sys.exit(1)
    platform_path = os.path.join(path('platform'), platform)
    print("Using forced platform '%s'" % platform)
else:
    for platform in platforms:
        f = open(os.path.join(path('platform'), platform, 'check.py'), 'U')
        try:
            exec f.read()
        except:
            print("Couldn't load platform '%s'" % platform)
        else:
            print("Using platform '%s'" % platform)
            platform_path = os.path.join(path('platform'), platform)
            break
        f.close()
        del f
    else:
        print("Cannot use any available platform")
        sys.exit(1)

sys.path = [
    platform_path,
    os.path.join(platform_path, "scripts"),
    userpath,
    os.path.join(userpath, "scripts"),
    os.curdir,
    os.path.join(os.curdir, "scripts"),
    path(),
    path("scripts")
    ] + sys.path

import events
import ui

if 'URK_NO_REMOTE' not in os.environ:
    import remote

    if remote.run(' '.join(sys.argv[1:])):
        sys.exit(0)

name = "urk"
long_name = "urk IRC"
version = 0, -1, "cvs"
long_version = "%s v%s" % (long_name, ".".join(str(x) for x in version))
website = "http://urk.sf.net/"
authors = ["Vincent Povirk", "Marc Liddell"]
copyright = "2005 %s" % ', '.join(authors)

def main():
    for script_path in set(sys.path[1:8:2]):
        try:
            suffix = os.extsep+"py"
            for script in os.listdir(script_path):
                if script.endswith(suffix):
                    try:
                        events.load(script)
                    except:
                        traceback.print_exc()
                        print "Failed loading script %s." % script
        except OSError:
            pass
    
    ui.start(' '.join(sys.argv[1:]))

if __name__ == "__main__":
    main()
