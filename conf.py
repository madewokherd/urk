import events

import __main__ as urk
import os

__CONF_FILE = os.path.join(urk.userpath,'urk.conf')

def __save(e):
    file(__CONF_FILE, "w").write(repr(conf))
events.register('Exit', 'post', __save)

class __confdict(dict):
    def __getitem__(self, key):
        if key in self:
            return dict.__getitem__(self, key)

if os.access(__CONF_FILE,os.R_OK):
    conf = __confdict(**eval(file(__CONF_FILE).read()))
else:
    conf = __confdict()
