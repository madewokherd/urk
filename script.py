def onStart(event):
    print "Omg, we've started"
    
def preJoin(event):
    print "pre", "join"
    
def dothebartmanJoin(event):
    print "bartman", "join"
    
def dothebartmanPart(event):
    print "bartmano", "part"

def onInput(event):
    event.window.write(event.text)
