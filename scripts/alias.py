import sys

from conf import conf
import events

aliases = conf.get("aliases",{
    'op':'"mode "+window.id+" +"+"o"*len(args)+" "+" ".join(args)',
    'deop':'"mode "+window.id+" -"+"o"*len(args)+" "+" ".join(args)',
    'voice':'"mode "+window.id+" +"+"v"*len(args)+" "+" ".join(args)',
    'devoice':'"mode "+window.id+" -"+"v"*len(args)+" "+" ".join(args)',
    'clear':'window.output.clear()',
    })

#if we're reloading, we need to get rid of old onCommand events
for i in globals().copy():
    if i.startswith("onCommand"):
        del globals()[i]

class CommandHandler:
    __slots__ = ["command"]
    def __init__(self, command):
        self.command = command
    def __call__(self, e):
        loc = sys.modules.copy()
        loc.update(e.__dict__)
        result = eval(self.command,loc)
        if isinstance(result,basestring):
            events.run(result,e.window,e.network)

for name in aliases:
    globals()['onCommand'+name.capitalize()] = CommandHandler(aliases[name])

def onCommandAlias(e):
    if e.args and 'r' in e.switches:
        name = e.args[0].lower()
        command = aliases[name]
        del aliases[name]
        conf['aliases'] = aliases
        e.window.write("* Deleted alias %s%s (was %s)" % (conf.get('command-prefix','/'),name,command))
        events.load(__name__,reloading=True)
    elif 'l' in e.switches:
        e.window.write("* Current aliases:")
        for i in aliases:
            e.window.write("*  %s%s: %s" % (conf.get('command-prefix','/'),i,aliases[i]))
    elif len(e.args) >= 2:
        name = e.args[0].lower()
        command = ' '.join(e.args[1:])
        aliases[name] = command
        conf['aliases'] = aliases
        e.window.write("* Created an alias %s%s to %s" % (conf.get('command-prefix','/'),name,command))
        events.load(__name__,reloading=True)
    elif len(e.args) == 1:
        name = e.args[0].lower()
        if name in aliases:
            e.window.write("* %s%s is an alias to %s" % (conf.get('command-prefix','/'),name,aliases[name]))
        else:
            e.window.write("* There is no alias %s%s" % (conf.get('command-prefix','/'),name))
    else:
        e.window.write(
"""Usage:
 /alias \x02name\x02 \x02expression\x02 to create or replace an alias
 /alias \x02name\x02 to look at an alias
 /alias -r \x02name\x02 to remove an alias
 /alias -l to see a list of aliases""")
 
def onClose(w):
    import windows
    
    if w.role == windows.ScriptWindow:
        buffer = w.output.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter())
        
        file(w.id, "w").write(text)
        events.load(w.id, True)
 
def onCommandEdit(e):
    filename = ''
    try:
        args = events.find_script(e.args[0])
        if args[1]:
            args[1].close()
        filename = args[2]
    except ImportError:
        pass
    if not filename:
        import urk
        filename = os.path.join(urk.userpath,'scripts',e.args[0])
        if not filename.endswith('.py'):
            filename += ".py"
        open(filename,'a').close()
    import ui, windows
    w = ui.windows.new(windows.ScriptWindow, None, filename)
    
    w.output.get_buffer().set_text(file(filename).read())
    w.activate()
