history = {}

def onKeyPress(e):
    if e.window not in history:
        history[e.window] = [], -1

    if e.key == 'Up':
        h, i = history[e.window]
        
        if i == -1:
            if e.window.input.text:
                h.insert(0, e.window.input.text)
                i = 0
        i += 1
        
        if i < len(h):                
            history[e.window] = h, i

            e.window.input.text = h[i]
            e.window.input.cursor = -1
            
    if e.key == 'Down':
        h, i = history[e.window]
        
        if i == -1:
            if e.window.input.text:
                h.insert(0, e.window.input.text)
                i = 0
                
        i -= 1
        
        if i > -1:
            history[e.window] = h, i

            e.window.input.text = h[i]
            e.window.input.cursor = -1
            
        elif i == -1:
            history[e.window] = h, i
        
            e.window.input.text = ''
            e.window.input.cursor = -1

def onInput(e):
    if e.window not in history:
        history[e.window] = [], -1

    if e.text:
        history[e.window][0].insert(0, e.text)
        
def onClose(window):
    if window in history:
        del history[window]
