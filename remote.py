import traceback

try:
    import gobject
    import dbus
    import dbus.service
    import dbus.glib
    DBUS = True
except ImportError:
    DBUS = False

import events
import ui

def run(command):
    pass

if DBUS:
    class UrkRemoteControl(dbus.service.Object):
        @dbus.service.method('net.sf.urk')
        def run(self, command):
            window = ui.windows.manager.get_active()
            events.run(command, window, window.network)

    def run(command):
        try:
            bus = dbus.SessionBus()
        except:
            print "NO DBUS"
            return
    
        try:
            urk_obj = bus.get_object('net.sf.urk', '/net/sf/urk')

            urk_iface = dbus.Interface(urk_obj, 'net.sf.urk')
            urk_iface.run(command)

            return True

        except:
            bus_name = dbus.service.BusName('net.sf.urk', bus)
            UrkRemoteControl(bus_name, '/net/sf/urk')
