import events
import conf

# delete this once it's loaded the first time
if conf.get("scripts_to_load") is None:
    conf.set("scripts_to_load", ["script.py"])

if __name__ == "__main__":
    import irc

    scripts_to_load = conf.get("scripts_to_load")
    for script in scripts_to_load:
        events.load(script)

    import ui
    
    events.trigger("Start")
    
    ui.start()
