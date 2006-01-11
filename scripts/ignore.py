import events
from conf import conf
import irc

def setupText(e):
    for mask in conf.get('ignore_masks',()):
        if irc.match_glob('%s!%s' % (e.source, e.address), mask):
            events.halt()

setupAction = setupNotice = setupCtcp = setupCtcpReply = setupText
