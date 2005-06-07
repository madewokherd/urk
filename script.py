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
    
def onStart(event):
    # FIXME, find a list of networks to join from somewhere, prolly conf
    #         then join them
    def list_of_networks_to_join_from_somewhere():
        return ["ANet", "BNet", "CNet"]
    
    on_start_networks = list_of_networks_to_join_from_somewhere()
    
    for network in on_start_networks:
        # FIXME, connect to it
        #        how do we do this?
        #        we prolly call something.connect(network)
        #        or else maybe we create a network object and call
        #        network_object.connect()
        
        print "Connecting to %s" % network
