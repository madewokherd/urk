import pprint

import events

import __main__ as urk
import os

CONF_FILE = os.path.join(urk.userpath,'urk.conf')

def save(e):
    pprint.pprint(conf, file(CONF_FILE, "w"))

events.register('Exit', 'post', save)

class confdict(dict):
    def __getitem__(self, key):
        if key in self:
            return dict.__getitem__(self, key)

if os.access(CONF_FILE,os.R_OK):
    conf = confdict(**eval(file(CONF_FILE).read()))
else:
    conf = confdict()
