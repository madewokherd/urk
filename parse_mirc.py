BOLD = '\x02'
UNDERLINE = '\x1F'
MIRC_COLOR = '\x03'
BERS_COLOR = '\x04'
RESET = '\x0F'

TAGS = BOLD, UNDERLINE, MIRC_COLOR, BERS_COLOR, RESET

colors = (
  'white', 'black', '#00007F', '#009300', 
  'red', '#7F0000', '#9C009C', '#FF7F00',
  'yellow', 'green', '#009393', '#00FFFF',
  '#0000FF', '#FF00FF', '#7F7F7F', '#D2D2D2'
  )

def get_mirc_color(number):
    return colors[int(number) & 15]
    
DEC_DIGITS, HEX_DIGITS = set('0123456789'), set('0123456789abcdefABCDEF')

def parse_mirc2(string):
    string += RESET

    out = ""
    looking = {}
    tags = []
    pos = 0

    while string:
        tag = string[0]

        if tag == MIRC_COLOR:
            if tag in looking:
                tags += [looking.pop(tag) + (pos,)]
            
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
                        
                    looking[tag] = [("foreground", fg), ("background", bg)], pos
                        
                else:
                    looking[tag] = [("foreground", fg)], pos 

        elif tag == BERS_COLOR:
            if tag in looking:
                tags += [looking.pop(tag) + (pos,)]

            if HEX_DIGITS.issuperset(string[1:7]):
                fg = "#" + string[1:7]

                if string[7:8] == "," and HEX_DIGITS.issuperset(string[8:14]):
                    bg = "#" + string[8:14]

                    looking[tag] = [("foreground", fg), ("background", bg)], pos
                    
                    string = string[13:]
                    
                else:
                    looking[tag] = [("foreground", fg)], pos
                    
                    string = string[6:]

        elif tag in (BOLD, UNDERLINE):
            if tag in looking:
                tags += [looking.pop(tag) + (pos,)]
            else:
                if tag == BOLD:
                    looking[tag] = [("weight", BOLD)], pos
                else:
                    looking[tag] = [("underline", UNDERLINE)], pos
        
        elif tag == RESET:
            for look in looking:
                tags += [looking[look] + (pos,)]
            looking = {}
                
        else:
            out += tag
            pos += 1
            
        string = string[1:]
        
    return tags, out
    
def parse_mirc_color(string, pos, looking, tags):
    if MIRC_COLOR in looking:
        tags += [looking.pop(MIRC_COLOR) + (pos,)]
    
    color_chars = 1

    if string[0] in DEC_DIGITS:
        if string[1:2] in DEC_DIGITS:
            fg = get_mirc_color(string[:2])
            string = string[1:]
            color_chars += 2

        else:
            fg = get_mirc_color(string[:1])
            color_chars += 1
            
        if string[1:2] == "," and string[2:3] in DEC_DIGITS:
            if string[3:4] in DEC_DIGITS:
                bg = get_mirc_color(string[2:4])
                color_chars += 3

            else:
                bg = get_mirc_color(string[2:3])
                color_chars += 2
                
            looking[MIRC_COLOR] = [("foreground", fg), ("background", bg)], pos
                
        else:
            looking[MIRC_COLOR] = [("foreground", fg)], pos 
                    
    return color_chars

def parse_bersirc_color(string, pos, looking, tags):
    if BERS_COLOR in looking:
        tags += [looking.pop(BERS_COLOR) + (pos,)]
            
    fg, bg = string[:6], string[7:13]        
    if HEX_DIGITS.issuperset(fg):
        if string[6:7] == "," and HEX_DIGITS.issuperset(bg):
            looking[BERS_COLOR] = [("foreground", "#" + fg), ("background", "#" + bg)], pos
            return 14
            
        else:
            looking[BERS_COLOR] = [("foreground", "#" + fg)], pos
            return 7
            
    else:
        return 1
    
def parse_bold(string, pos, looking, tags):
    if BOLD in looking:
        tags += [looking.pop(BOLD) + (pos,)]
        
    else:
        looking[BOLD] = [("weight", BOLD)], pos
        
    return 1
    
def parse_underline(string, pos, looking, tags):
    if UNDERLINE in looking:
        tags += [looking.pop(UNDERLINE) + (pos,)]
        
    else:
        looking[UNDERLINE] = [("underline", UNDERLINE)], pos
        
    return 1

def parse_reset(string, pos, looking, tags):
    for look in looking:
        tags += [looking[look] + (pos,)]
    looking.clear()
    
    return 1

def parse_mirc(string):
    string += RESET

    out = ''
    looking = {}
    tags = []
    last_place = pos = 0
    
    tag_fs = {
        MIRC_COLOR: parse_mirc_color,
        BERS_COLOR: parse_bersirc_color,
        BOLD: parse_bold,
        UNDERLINE: parse_underline,
        RESET: parse_reset
        }

    for tag_place, tag in [(i, s) for i, s in enumerate(string) if s in tag_fs]:
        out += string[last_place:tag_place]

        pos += tag_place - last_place
        
        last_place = tag_place + tag_fs[tag](
                                    string[tag_place+1:], 
                                    pos, 
                                    looking,
                                    tags
                                    )
        
    return tags, out

if __name__ == "__main__":
    tests = [
        'not\x02bold\x02not',
        'not\x1Funderline\x1Fnot',
        
        "\x02\x1FHi\x0F",
        
        'not\x030,17white-on-black\x0304red-on-black\x03nothing',
        
        "\x040000CC<\x04nick\x040000CC>\x04 text",
        
        '\x04770077,FFFFFFbersirc color with background! \x04000077setting foreground! \x04reset!',
        
        '\x047700,FFFFbersirc',
        
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
        
    #"""
    
    r = range(5000)    
    for i in r:
        for test in tests:
            parse_mirc(test)
            parse_mirc2(test)
            
    """
    
    r = range(1)    
    for i in r:
        for test in tests:
            print test
            print parse_mirc(test)
            print parse_mirc2(test)
            print
            pass
            
            
                
   #"""
   
#import dis
#dis.dis(parse_mirc)
