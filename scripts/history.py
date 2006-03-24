def onKeyPress(e):
    if not hasattr(e.window, 'history'):
        e.window.history = [], -1

    if e.key == 'Up':
        h, i = e.window.history
        
        if i == -1:
            if e.window.input.text:
                h.insert(0, e.window.input.text)
                i = 0
        i += 1
        
        if i < len(h):                
            e.window.history = h, i

            e.window.input.text = h[i]
            e.window.input.cursor = -1
            
    if e.key == 'Down':
        h, i = e.window.history
        
        if i == -1:
            if e.window.input.text:
                h.insert(0, e.window.input.text)
                i = 0
                
        i -= 1
        
        if i > -1:
            e.window.history = h, i

            e.window.input.text = h[i]
            e.window.input.cursor = -1
            
        elif i == -1:
            e.window.history = h, i
        
            e.window.input.text = ''
            e.window.input.cursor = -1

def onInput(e):
    if not hasattr(e.window, 'history'):
        e.window.history = [], -1

    if e.text:
        h, i = e.window.history
    
        h.insert(0, e.text)
        
        e.window.history = h, -1
