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
    
DEC_DIGITS, HEX_DIGITS = set('0123456789'), set('0123456789abcdefABCDEF')

def ishex(string):
    return set(string) < HEX_DIGITS

def parse_mirc(string):
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
    
    r = range(5000)    
    for i, f in to_test.items():
        print "parse_mirc%s" % i 
           
        for i in r:
            for test in tests:
                f(test)
                
   #"""
