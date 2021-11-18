import events

import urk

import tempfile
import shutil
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
    data = pprint(conf)
    reloaded_conf = eval(data)
    if reloaded_conf != conf:
        raise Exception("Configuration round-trip failed")
    fd, new_file = tempfile.mkstemp()
    os.chmod(new_file,0600)
    os.close(fd)
    fd = file(new_file, "wb")
    try:
        fd.write(data)
        fd.close()
        shutil.move(new_file, CONF_FILE)
    finally:
        fd.close()

events.register('Exit', 'post', save)

try:
    conf = eval(file(CONF_FILE, "U").read().strip())
except IOError, e:
    if e.args[0] == 2:
        conf = {}
    else:
        raise
    
if __name__ == '__main__':
    print pprint(conf)
