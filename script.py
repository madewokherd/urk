import events

def onCommand(e):
    if e.name == "flag":
        e.done = True
        
        events.run_command("say - %s" % e.switches, e.window, e.window.network)

def onRightClick(e):
    def print_blah():
        print "blah"
        
    e.menu.append(("RightClick", print_blah))
    
def onListRightClick(e):
    def print_blah():
        print "blah"
        
    e.menu.append(("ListRightClick", print_blah))
    
def onWindowMenu(e):
    def print_blah():
        print "blah"
        
    e.menu.append(("WindowMenu", print_blah))

def defCommand(e):
    if not e.done:
        if 'handle_%s' % e.name in globals():
            globals()['handle_%s' % e.name](e)
