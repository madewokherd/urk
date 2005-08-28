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
    
DEC_DIGITS, HEX_DIGITS = set('0123456789'), set('0123456789ABCDEF')

def ishex(string):
    for char in string.upper():
        if char not in HEX_DIGITS:
            return False
    
    return bool(string)

def parse_mirc1(string):
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
    
def parse_mirc2(string):
    out, looking, tags, pos = "", {}, [], 0
    
    string += RESET

    while string:
        c = string[0]

        if c == MIRC_COLOR:
            if c in looking:
                tags.append(looking[c] + (pos,))
                del looking[c]
            
            if string[1:2] in DEC_DIGITS:
                if string[2:3] in DEC_DIGITS:
                    fg, string = get_mirc_color(string[1:3]), string[2:]

                else:
                    fg, string = get_mirc_color(string[1:2]), string[1:]
                    
                if string[1:2] == "," and string[2:3] in DEC_DIGITS:
                    if string[3:4] in DEC_DIGITS:
                        bg, string = get_mirc_color(string[2:4]), string[3:]

                    else:
                        bg, string = get_mirc_color(string[2:3]), string[2:]
                        
                    looking[c] = [("foreground", fg), ("background", bg)], pos
                        
                else:
                    looking[c] = [("foreground", fg)], pos 

        elif c == BERS_COLOR:
            if c in looking:
                tags.append(looking[c] + (pos,))
                del looking[c]

            if ishex(string[1:7]):
                fg, string = "#" + string[1:7], string[6:]

                if string[1:2] == "," and ishex(string[2:8]):
                    bg, string = "#" + string[2:8], string[7:]

                    looking[c] = [("foreground", fg), ("background", bg)], pos
                    
                else:
                    looking[c] = [("foreground", fg)], pos
                    
        elif c in (BOLD, UNDERLINE):
            if c in looking:
                tags.append(looking[c] + (pos,))
                del looking[c]
        
            else:
                if c == BOLD:
                    looking[c] = [("weight", BOLD)], pos
                else:
                    looking[c] = [("underline", UNDERLINE)], pos
        
        elif c == RESET:
            for look in looking:
                tags.append(looking[look] + (pos,))
            looking = {}
                
        else:
            out += c
            pos += 1
            
        string = string[1:]

    return tags, out
        
def parse_mirc3(string):
    codes = MIRC_COLOR, BERS_COLOR, BOLD, UNDERLINE, RESET
    tokill = {}

    tags = dict([(c, []) for c in codes])
    for i, s in enumerate(string + RESET):
        if s in codes:
            tokill[i] = 1
        
            tags[s] += [i]

            if s == RESET:
                for t in tags:
                    tags[t] += [i]

    ntags = []
                
    for p1, p2 in zip(tags[BOLD][::2], tags[BOLD][1::2]):
        ntags.append(([("weight", BOLD)], p1, p2))
        
    for p1, p2 in zip(tags[UNDERLINE][::2], tags[UNDERLINE][1::2]):
        ntags.append(([("underline", UNDERLINE)], p1, p2))

    for p1, p2 in zip(tags[MIRC_COLOR], tags[MIRC_COLOR][1:]):
        next = string[p1+1:p1+6]
        
        g, GET = {"f": "", "b": ""}, "f"

        while next:
            if next[0] in DEC_DIGITS and len(g[GET]) <= 1:
                g[GET] += next[0]
                
            elif next[0] == ",":
                if not (g["f"] and next[1:] and next[1] in DEC_DIGITS):
                    break
                    
                else:
                    GET = "b"
            else:
                break

            next = next[1:]
            
        if g["f"]:
            fg = get_mirc_color(g["f"])

            if g["b"]:
                bg = get_mirc_color(g["b"])

                tokill[p1+len(g["f"] + g["b"])+1] = len(g["f"] + g["b"]) + 1
                
                ntags.append(([("foreground", fg), ("background", bg)], p1, p2))
                
            else:
                tokill[p1+len(g["f"])] = len(g["f"])
            
                ntags.append(([("foreground", fg)], p1, p2))
                            
    for p1, p2 in zip(tags[BERS_COLOR], tags[BERS_COLOR][1:]):
        next = string[p1+1:p1+14]

        if ishex(next[0:6]):
            fg, bg = "#" + next[0:6], ""
            
            if next[6:7] == ",":
                if next[12:] and ishex(next[7:13]):
                    bg = "#" + next[7:13]

            if bg:
                tokill[p1+13] = 13
                
                ntags.append(([("foreground", fg), ("background", bg)], p1, p2))
            else:
                tokill[p1+6] = 6
                
                ntags.append(([("foreground", fg)], p1, p2))

    out = list(string + " ") 
    for i in sorted(tokill, reverse=True):
        del out[i-tokill[i]+1:i+1]
    
        for j, tag in enumerate(ntags):
            p, fr, to = tag
            
            if i < fr:
                fr -= tokill[i]
            if i < to:
                to -= tokill[i]
                
            ntags[j] = p, fr, to

    return ntags, "".join(out)
    
parse_mirc = parse_mirc2

if __name__ == "__main__":
    tests = [
        'not\x02bold\x02not',
        'not\x1Funderline\x1Fnot',
        
        "\x02\x1FHi\x0F",
        
        'not\x030,17white-on-black\x0304red-on-black\x03nothing',
        
        "\x040000CC<\x04nick\x040000CC>\x04 text",
        
        '\x04770077,FFFFFFbersirc color with background! \x04000077setting foreground! \x04reset!',
        
        "\x03123Hello",
        
        "\x0312,Hello",
        
        "\x034Hello",
        
        "Bo\x02ld",
        ]
        
    results = [
        ([([('weight', BOLD)], 3, 7)], 'notboldnot'),
        ([([('underline', UNDERLINE)], 3, 12)], 'notunderlinenot'),
        
        ([([('underline', BOLD), ('weight', UNDERLINE)], 0, 2)], 'Hi'),

        
        ([([('foreground', 'white'), ('background', 'black')], 3, 17), ([('foreground', 'red'), ('background', 'black')], 17, 29)], 'notwhite-on-blackred-on-blacknothing'),
        
        ([([('foreground', '#0000CC')], 0, 1), ([('foreground', '#0000CC')], 5, 6)], '<nick> text'),
        ([([('foreground', '#770077'), ('background', '#FFFFFF')], 0, 31), ([('foreground', '#000077'), ('background', '#FFFFFF')], 31, 51)], 'bersirc color with background! setting foreground! reset!'),
        ]
        
    """
        
    for test in tests:
        print parse_mirc2(test)

    """

    to_test = {
        #1: parse_mirc1, 
        2: parse_mirc2,
        #3: parse_mirc3,
        }
    
    r = range(1000)    
    for i, f in to_test.items():
        print "parse_mirc%s" % i 
           
        for i in r:
            for test in tests:
                f(test)
                
   #"""
