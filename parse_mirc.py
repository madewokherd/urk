BOLD = '\x02'
UNDERLINE = '\x1F'
REVERSE = '\x16'
MIRC_COLOR = '\x03'
BERS_COLOR = '\x04'
RESET = '\x0F'

colors = (
  'white', 'black', '#00007F', '#009300', 
  'red', '#7F0000', '#9C009C', '#FF7F00',
  'yellow', 'green', '#009393', '#00FFFF',
  '#0000FF', '#FF00FF', '#7F7F7F', '#D2D2D2')

def get_mirc_color(number):
    return colors[int(number) % len(colors)]

def ishex(string):
    for char in string:
        if char.upper() not in '0123456789ABCDEF':
            return False
    return True

def parse_mirc(string):
    start = 0
    pos = 0
    props = {}
    tag_data = []
    new_string = ''
    while pos < len(string):
        char = string[pos]
        if char == BOLD: #bold
            if start != len(new_string):
                if props:
                    tag_data.append((props.items(), start, len(new_string)))
                start = len(new_string)
            if 'weight' in props:
                del props['weight']
            else:
                props['weight'] = BOLD
            pos += 1
        elif char == UNDERLINE: #underline
            if start != len(new_string):
                if props:
                    tag_data.append((props.items(), start, len(new_string)))
                start = len(new_string)
            if 'underline' in props:
                del props['underline']
            else:
                props['underline'] = UNDERLINE
            pos += 1
        elif char == REVERSE: #reverse
            if start != len(new_string):
                if props:
                    tag_data.append((props.items(), start, len(new_string)))
                start = len(new_string)
            #This isn't entirely correct, but reverse is rarely used and I'd
            # need to add extra state to really do it correctly
            if props.get('foreground') == 'white' and \
              props.get('background' == 'black'):
                del props['foreground']
                del props['background']
            else:
                props['foreground'] = 'white'
                props['background'] = 'black'
            pos += 1
        elif char == MIRC_COLOR: #khaled color
            if start != len(new_string):
                if props:
                    tag_data.append((props.items(), start, len(new_string)))
                start = len(new_string)
            pos += 1
            if pos < len(string) and string[pos].isdigit():
                fg = string[pos]
                pos += 1
                if pos < len(string) and string[pos].isdigit():
                    fg += string[pos]
                    pos += 1
                if fg != '99':
                    props['foreground'] = get_mirc_color(fg)
                elif 'foreground' in props:
                    del props['foreground']
                if pos+1 < len(string) and string[pos] == ',' and string[pos+1].isdigit():
                    bg = string[pos+1]
                    pos += 2
                    if pos < len(string) and string[pos].isdigit():
                        bg += string[pos]
                        pos += 1
                    if bg != '99':
                        props['background'] = get_mirc_color(bg)
                    elif 'background' in props:
                        del props['background']
            else:
                if 'foreground' in props:
                    del props['foreground']
                if 'background' in props:
                    del props['background']
        elif char == BERS_COLOR: #bersirc color
            if start != len(new_string):
                if props:
                    tag_data.append((props.items(), start, len(new_string)))
                start = len(new_string)
            pos += 1
            if pos+5 < len(string) and ishex(string[pos:pos+6]):
                fg = '#'+string[pos:pos+6]
                pos += 6
                props['foreground'] = fg
                if pos+6 < len(string) and string[pos] == ',' and ishex(string[pos+1:pos+7]):
                    bg = '#'+string[pos+1:pos+7]
                    pos += 7
                    props['background'] = bg
            else:
                if 'foreground' in props:
                    del props['foreground']
                if 'background' in props:
                    del props['background']
        elif char == RESET: #reset formatting
            if start != len(new_string):
                if props:
                    tag_data.append((props.items(), start, len(new_string)))
                start = len(new_string)
            props.clear()
            pos += 1
        else:
            new_string += char
            pos += 1
    if start != len(new_string) and props:
        tag_data.append((props.items(), start, len(new_string)))
    return tag_data, new_string                
    
if __name__ == "__main__":
    tests = [
        'not\x02bold\x02not',
        'not\x1Funderline\x1Fnot',
        
        "\x02\x1FHi\x0F",
        
        'not\x030,17white-on-black\x0304red-on-black\x03nothing',
        
        "\x040000CC<\x04nick\x040000CC>\x04 text",
        
        '\x04770077,FFFFFFbersirc color with background! \x04000077setting foreground! \x04reset!',
        ]
        
    results = [
        ([([('weight', BOLD)], 3, 7)], 'notboldnot'),
        ([([('underline', UNDERLINE)], 3, 12)], 'notunderlinenot'),
        
        ([([('underline', BOLD), ('weight', UNDERLINE)], 0, 2)], 'Hi'),

        
        ([([('foreground', 'white'), ('background', 'black')], 3, 17), ([('foreground', 'red'), ('background', 'black')], 17, 29)], 'notwhite-on-blackred-on-blacknothing'),
        
        ([([('foreground', '#0000CC')], 0, 1), ([('foreground', '#0000CC')], 5, 6)], '<nick> text'),
        ([([('foreground', '#770077'), ('background', '#FFFFFF')], 0, 31), ([('foreground', '#000077'), ('background', '#FFFFFF')], 31, 51)], 'bersirc color with background! setting foreground! reset!'),
        ]   
    
