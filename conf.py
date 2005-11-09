import events

import __main__ as urk
import os

CONF_FILE = os.path.join(urk.userpath,'urk.conf')

def pprint(x, depth=-2):
    depth += 2
    
    s_list = []

    if isinstance(x, dict):
        s_list = s_list + ['{', '\n']
    
        for key in x:
            s_list += ['%s%s%s' % (' '*depth, repr(key), ':')]
            s_list += pprint(x[key], depth)
            
        s_list += ['%s%s' % (' '*depth, '}')]
        s_list += [',\n']
        
    elif isinstance(x, list):
        s_list += ['[', '\n']
    
        for item in x:
            s_list += ['%s' % (' '*depth)]
            s_list += pprint(item, depth)
            
        s_list += ['%s%s' % (' '*depth, ']')]
        s_list += [',\n']
        
    else:
        s_list += ['%s,' % repr(x), '\n']
        
    if depth == 0:
        return ''.join(s_list[:-1])
    
    else:
        return s_list

def save(e):
    file(CONF_FILE, "w").write(pprint(conf))

events.register('Exit', 'post', save)

class confdict(dict):
    def __getitem__(self, key):
        if key in self:
            return dict.__getitem__(self, key)

if os.access(CONF_FILE,os.R_OK):
    conf = confdict(**eval(file(CONF_FILE).read()))
else:
    conf = confdict()
