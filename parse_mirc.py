BOLD = '\x02'
UNDERLINE = '\x1F'
MIRC_COLOR = '\x03'
BERS_COLOR = '\x04'
RESET = '\x0F'

colors = (
  'white', 'black', '#00007F', '#009300', 
  'red', '#7F0000', '#9C009C', '#FF7F00',
  'yellow', 'green', '#009393', '#00FFFF',
  '#0000FF', '#FF00FF', '#7F7F7F', '#D2D2D2'
  )

def get_mirc_color(number):
    if number != '99':
        return colors[int(number) & 15]
    
DEC_DIGITS, HEX_DIGITS = set('0123456789'), set('0123456789abcdefABCDEF')

ishex = HEX_DIGITS.issuperset
    
def parse_mirc_color(string, pos, open_tags, tags):
    color_chars = 1

    bg = None
    if MIRC_COLOR in open_tags:
        tag = open_tags.pop(MIRC_COLOR)
        tags += [tag + (pos,)]
        
        if len(tag[0]) > 1:
            bg = tag[0][1][1]

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
        
        tag = []
        if fg:
            tag.append(("foreground",fg))
        if bg:
            tag.append(("background",bg))
        if tag:
            open_tags[MIRC_COLOR] = (tag, pos) 
              
    return color_chars

def parse_bersirc_color(string, pos, open_tags, tags):      
    fg = string[:6]
    
    bg = None
    if BERS_COLOR in open_tags:
        tag = open_tags.pop(BERS_COLOR)
        tags += [tag + (pos,)]
        
        if len(tag[0]) > 1:
            bg = tag[0][1][1]
    
    if ishex(fg):
        if string[6:7] == "," and ishex(string[7:13]):
            bg = string[7:13]
        
            open_tags[BERS_COLOR] = ([("foreground", "#" + fg), ("background", "#" + bg)], pos)
            return 14
            
        elif bg:
            open_tags[BERS_COLOR] = ([("foreground", "#" + fg), ("background", "#" + bg)], pos)
            return 7
            
        else:
            open_tags[BERS_COLOR] = ([("foreground", "#" + fg)], pos)
            return 7
            
    else:
        return 1
    
def parse_bold(string, pos, open_tags, tags):
    if BOLD in open_tags:
        tags += [open_tags.pop(BOLD) + (pos,)]
        
    else:
        open_tags[BOLD] = [("weight", BOLD)], pos
        
    return 1
    
def parse_underline(string, pos, open_tags, tags):
    if UNDERLINE in open_tags:
        tags += [open_tags.pop(UNDERLINE) + (pos,)]
        
    else:
        open_tags[UNDERLINE] = [("underline", UNDERLINE)], pos
        
    return 1

def parse_reset(string, pos, open_tags, tags):
    for tag in open_tags:
        if isinstance(open_tags[tag], list):
            for l in open_tags[tag]:
                tags += [l + (pos,)]
                
        else:
            tags += [open_tags[tag] + (pos,)]

    open_tags.clear()
    
    return 1

def parse_mirc(string):
    string += RESET

    out = ''
    open_tags = {}
    tags = []
    last_place = pos = 0
    
    tag_fs = {
        MIRC_COLOR: parse_mirc_color,
        BERS_COLOR: parse_bersirc_color,
        BOLD: parse_bold,
        UNDERLINE: parse_underline,
        RESET: parse_reset
        }

    for tag_place, tag_f in [(i, tag_fs[s]) for i, s in enumerate(string) if s in tag_fs]:
        out += string[last_place:tag_place]

        pos += tag_place - last_place
        
        last_place = tag_place + tag_f(
                                    string[tag_place+1:], 
                                    pos, 
                                    open_tags,
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
        
        "\x034,5Hello\x036Goodbye",
        
        "\x04ff0000,00ff00Hello\x040000ffGoodbye",
        
        "\x04777777(\x0400CCCCstuff\x04777777)\x04"
        ]
        
    results = [
        ([([('weight', '\x02')], 3, 7)], 'notboldnot'),

        ([([('underline', '\x1f')], 3, 12)], 'notunderlinenot'),

        ([([('weight', '\x02')], 0, 2), ([('underline', '\x1f')], 0, 2)], 'Hi'),

        ([([('foreground', 'white'), ('background', 'black')], 3, 29), ([('foreground', 'red')], 17, 29)], 'notwhite-on-blackred-on-blacknothing'),

        ([([('foreground', '#0000CC')], 0, 1), ([('foreground', '#0000CC')], 5, 6)], '<nick> text'),

        ([([('foreground', '#770077'), ('background', '#FFFFFF')], 0, 51), ([('foreground', '#000077')], 31, 51)], 'bersirc color with background! setting foreground! reset!'),

        ([], '7700,FFFFbersirc'),

        ([([('foreground', '#0000FF')], 0, 6)], '3Hello'),

        ([([('foreground', '#0000FF')], 0, 6)], ',Hello'),

        ([([('foreground', 'red')], 0, 5)], 'Hello'),

        ([([('weight', '\x02')], 2, 4)], 'Bold'),

        ([([('foreground', 'red'), ('background', '#7F0000')], 0, 12), ([('foreground', '#9C009C')], 5, 12)], 'HelloGoodbye'),

        ([([('foreground', '#ff0000'), ('background', '#00ff00')], 0, 12), ([('foreground', '#0000ff')], 5, 12)], 'HelloGoodbye'),
        ]
        
    #"""
    
    print parse_mirc(tests[-1])
    
    r = range(500)    
    for i in r:
        for test in tests:
            parse_mirc(test)
            
    """
    
    r = range(1)    
    for i in r:
        for test, result in zip(tests, results):
            print parse_mirc(test) == result
        
   #"""
   
#import dis
#dis.dis(parse_mirc)
