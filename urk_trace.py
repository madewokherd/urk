import sys
import commands
import linecache

def traceit(frame, event, arg):
    if event == "line":
        mem = " " + commands.getoutput(
                "ps -eo cmd,rss | grep urk_trace.py | grep -v grep"
                ).split(" ")[-1]
    
        try:
            filename = frame.f_globals["__file__"]
            
            if filename.endswith(".pyc") or filename.endswith(".pyo"):
                filename = filename[:-1]
                
            name = frame.f_globals["__name__"]
        
            lineno = frame.f_lineno
            line = linecache.getline(filename,lineno).rstrip()
            
            data = "%s:%i: %s" % (name, lineno, line)
        
            print "%s%s" % (data, mem.rjust(80 - len(data)))
        except:
            pass

    return traceit
    
def main():
    import urk
    urk.main()

sys.settrace(traceit)
main()
