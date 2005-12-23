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

if DBUS:
    class UrkRemoteControl(dbus.service.Object):
        def __init__(self, bus_name, object_path='/net/sf/urk/RemoteControl'):
            dbus.service.Object.__init__(self, bus_name, object_path)
    
        @dbus.service.method('net.sf.urk.RemoteControlIFace')
        def run(self, command):
            window = ui.windows.manager.get_active()
            events.run(command, window, window.network)

    def doit_remotely(x):
        try:
            bus = dbus.SessionBus()
            proxy_obj = bus.get_object('net.sf.urk', '/net/sf/urk/RemoteControl')
                
            iface = dbus.Interface(proxy_obj, 'net.sf.urk.RemoteControlIFace')
            iface.run(x)
            
            return True

        except:
            traceback.print_exc()
            
    def start_service():
        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName('net.sf.urk', bus=bus)
        UrkRemoteControl(bus_name)
else:
    class UrkRemoteControl:
        def __init__(self, *args, **kwargs):
            pass
        def run(self, command):
            window = ui.windows.manager.get_active()
            events.run(command, window, window.network)
    def doit_remotely(x):
        pass
    def start_service():
        pass
