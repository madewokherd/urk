import events

__CONF_FILE = "/home/marc/urk.conf"

def __save(e):
    file(__CONF_FILE, "w").write(repr(conf))
events.register('Exit', 'post', __save)

class __confdict(dict):
    def __getitem__(self, key):
        if key in self:
            return dict.__getitem__(self, key)

conf = __confdict(**eval(file(__CONF_FILE).read()))
