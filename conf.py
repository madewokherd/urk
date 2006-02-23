import events

import urk
import os

CONF_FILE = os.path.join(urk.userpath,'urk.conf')

def pprint(obj, depth=-2):
    depth += 2
    
    string = []

    if isinstance(obj, dict):
        if obj:
            string.append('{\n')
        
            for key in obj:
                string.append('%s%s%s' % (' '*depth, repr(key), ': '))
                string += pprint(obj[key], depth)
                
            string.append('%s%s' % (' '*depth, '},\n'))
            
        else:
            string.append('{},\n')
        
    elif isinstance(obj, list):
        if obj:
            string.append('[\n')
        
            for item in obj:
                string.append('%s' % (' '*depth))
                string += pprint(item, depth)
                
            string.append('%s%s' % (' '*depth, '],\n'))
            
        else:
            string.append('[],\n')
        
    else:
        string.append('%s,\n' % (repr(obj),))
        
    if depth:
        return string
    else:
        return ''.join(string)[:-2]

def save(*args):
    new_file = not os.access(CONF_FILE,os.F_OK)
    fd = file(CONF_FILE, "wb")
    try:
        if new_file:
            os.chmod(CONF_FILE,0600)
        fd.write(pprint(conf))
    finally:
        fd.close()

events.register('Exit', 'post', save)

if os.access(CONF_FILE,os.R_OK):
    conf = eval(file(CONF_FILE, "U").read().strip())
else:
    conf = {}
    
if __name__ == '__main__':
    print pprint(conf)
