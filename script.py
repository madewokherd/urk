
def onRightClick(event):
    def print_blah():
        print "blah"
        
    event.menu.append(("RightClick", print_blah))
    
def onListRightClick(event):
    def print_blah():
        print "blah"
        
    event.menu.append(("ListRightClick", print_blah))
    
def onWindowMenu(event):
    def print_blah():
        print "blah"
        
    event.menu.append(("WindowMenu", print_blah))

def defCommand(event):
    if not event.done:
        if 'handle_%s' % event.name in globals():
            globals()['handle_%s' % event.name](event)
