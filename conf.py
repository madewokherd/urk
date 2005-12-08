import events

import urk
import os

CONF_FILE = os.path.join(urk.userpath,'urk.conf')

def pprint(x, depth=-2):
    depth += 2
    
    s_list = []

    if isinstance(x, dict):
        s_list += ['{', '\n']
    
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
    new_file = not os.access(CONF_FILE,os.F_OK)
    fd = file(CONF_FILE, "w")
    try:
        if new_file:
            os.chmod(CONF_FILE,0600)
        fd.write(pprint(conf))
    finally:
        fd.close()

events.register('Exit', 'post', save)

if os.access(CONF_FILE,os.R_OK):
    conf = eval(file(CONF_FILE).read().strip())
else:
    conf = {}
