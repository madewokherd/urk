import sys

from conf import conf
import events

aliases = conf.get("aliases",{
    'op':'"mode "+window.id+" +ooo "+" ".join(args)',
    'deop':'"mode "+window.id+" -ooo "+" ".join(args)',
    'voice':'"mode "+window.id+" +ooo "+" ".join(args)',
    'devoice':'"mode "+window.id+" -ooo "+" ".join(args)',
    'clear':'window.output.get_buffer().set_text("")',
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
