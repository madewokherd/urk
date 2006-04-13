from conf import conf

BOLD = '\x02'
UNDERLINE = '\x1F'
MIRC_COLOR = '\x03'
MIRC_COLOR_BG = MIRC_COLOR, MIRC_COLOR
BERS_COLOR = '\x04'
BERS_COLOR_BG = BERS_COLOR, BERS_COLOR
RESET = '\x0F'

COLOR_99 = '\x00'

colors = (
  'white', 'black', '#00007F', '#009300', 
  'red', '#7F0000', '#9C009C', '#FF7F00',
  'yellow', 'green', '#009393', '#00FFFF',
  '#0000FF', '#FF00FF', '#7F7F7F', '#D2D2D2'
  )

def get_mirc_color(number):
    if number == '99':
        return COLOR_99

    number = int(number) & 15
    
    confcolors = conf.get('colors', colors)
    try:
        return confcolors[number]
    except:
        # someone edited their colors wrongly
        return colors[number]
    
DEC_DIGITS, HEX_DIGITS = set('0123456789'), set('0123456789abcdefABCDEF')
    
def parse_mirc_color(string, pos, open_tags, tags):
    color_chars = 1

    bg = None
    if MIRC_COLOR in open_tags:
        fgtag = open_tags.pop(MIRC_COLOR)
        fgtag['to'] = pos
        tags.append(fgtag)
        
        if MIRC_COLOR_BG in open_tags:
            bgtag = open_tags.pop(MIRC_COLOR_BG)
            bgtag['to'] = pos
            tags.append(bgtag)

            bg = bgtag['data']

    if string[0] in DEC_DIGITS:   
        if string[1] in DEC_DIGITS:
            fg = "foreground", get_mirc_color(string[:2])
            string = string[1:]
            color_chars += 2

        else:
            fg = "foreground", get_mirc_color(string[0])
            color_chars += 1
        
        if string[1] == "," and string[2] in DEC_DIGITS:
            if string[3] in DEC_DIGITS:
                bg = "background", get_mirc_color(string[2:4])
                color_chars += 3

            else:
                bg = "background", get_mirc_color(string[2])
                color_chars += 2

            open_tags[MIRC_COLOR] = {'data': fg, 'from': pos}
            open_tags[MIRC_COLOR_BG] = {'data': bg, 'from': pos}
                
        elif bg:
            open_tags[MIRC_COLOR] = {'data': fg, 'from': pos}
            open_tags[MIRC_COLOR_BG] = {'data': bg, 'from': pos}

        else:
            open_tags[MIRC_COLOR] = {'data': fg, 'from': pos}
              
    return color_chars

def parse_bersirc_color(string, pos, open_tags, tags):
    old_bg = None
    if BERS_COLOR in open_tags:
        tag = open_tags.pop(BERS_COLOR)
        tag['to'] = pos
        tags.append(tag)
        
        if BERS_COLOR_BG in open_tags:
            bgtag = open_tags.pop(BERS_COLOR_BG)
            bgtag['to'] = pos
            tags.append(bgtag)

            bg = bgtag['data']

    for c in (0, 1, 2, 3, 4, 5):
        if string[c] not in HEX_DIGITS:
            return 1
    fg = ('foreground', '#' + string[:6])

    for c in (7, 8, 9, 10, 11, 12):
        if string[c] not in HEX_DIGITS:
            break
    else:
        if string[6] == ",":
            open_tags[BERS_COLOR] = {'data': fg, 'from': pos}
            open_tags[BERS_COLOR_BG] = {
                'data': ('background', '#' + string[7:13]),
                'from': pos
                }
            return 14
        
    if old_bg:
        open_tags[BERS_COLOR] = {'data': fg, 'from': pos}
        open_tags[BERS_COLOR_BG] = {'data': old_bg, 'from': pos}
        return 7
        
    else:
        open_tags[BERS_COLOR] = {'data': fg, 'from': pos}
        return 7
    
def parse_bold(string, pos, open_tags, tags):
    if BOLD in open_tags:
        tag = open_tags.pop(BOLD)
        tag['to'] = pos
        tags.append(tag)
        
    else:
        open_tags[BOLD] = {'data': ('weight', BOLD), 'from': pos}

    return 1

def parse_underline(string, pos, open_tags, tags):
    if UNDERLINE in open_tags:
        tag = open_tags.pop(UNDERLINE)
        tag['to'] = pos
        tags.append(tag)
        
    else:
        open_tags[UNDERLINE] = {'data': ('underline', UNDERLINE), 'from': pos}
        
    return 1

def parse_reset(string, pos, open_tags, tags):
    for t in open_tags:
        tag = open_tags[t]
        tag['to'] = pos
        tags.append(tag)

    open_tags.clear()
    
    return 1

tag_fs = {
    MIRC_COLOR: parse_mirc_color,
    BERS_COLOR: parse_bersirc_color,
    BOLD: parse_bold,
    UNDERLINE: parse_underline,
    RESET: parse_reset
    }

def parse_mirc(string):
    string += RESET

    out = ''
    open_tags = {}
    tags = []
    text_i = outtext_i = 0

    for tag_i, char in enumerate(string):
        if char in tag_fs:
            out += string[text_i:tag_i]

            outtext_i += tag_i - text_i

            text_i = tag_i + tag_fs[char](
                                string[tag_i+1:], 
                                outtext_i, 
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
        ([{'from': 3, 'data': ('weight', '\x02'), 'to': 7}], 'notboldnot'),

        ([{'from': 3, 'data': ('underline', '\x1f'), 'to': 12}], 'notunderlinenot'),

        ([{'from': 0, 'data': ('weight', '\x02'), 'to': 2}, {'from': 0, 'data': ('underline', '\x1f'), 'to': 2}], 'Hi'),

        ([{'from': 3, 'data': ('foreground', 'white'), 'to': 17}, {'from': 3, 'data': ('background', 'black'), 'to': 17}, {'from': 17, 'data': ('foreground', 'red'), 'to': 29}, {'from': 17, 'data': ('background', 'black'), 'to': 29}], 'notwhite-on-blackred-on-blacknothing'),

        ([{'from': 0, 'data': ('foreground', '#0000CC'), 'to': 1}, {'from': 5, 'data': ('foreground', '#0000CC'), 'to': 6}], '<nick> text'),

        ([{'from': 0, 'data': ('foreground', '#770077'), 'to': 31}, {'from': 0, 'data': ('background', '#FFFFFF'), 'to': 31}, {'from': 31, 'data': ('foreground', '#000077'), 'to': 51}], 'bersirc color with background! setting foreground! reset!'),

        ([], '7700,FFFFbersirc'),
        
        ([{'from': 0, 'data': ('foreground', '#0000FF'), 'to': 6}], '3Hello'),

        ([{'from': 0, 'data': ('foreground', '#0000FF'), 'to': 6}], ',Hello'),

        ([{'from': 0, 'data': ('foreground', 'red'), 'to': 5}], 'Hello'),

        ([{'from': 2, 'data': ('weight', '\x02'), 'to': 4}], 'Bold'),

        ([{'from': 0, 'data': ('foreground', 'red'), 'to': 5}, {'from': 0, 'data': ('background', '#7F0000'), 'to': 5}, {'from': 5, 'data': ('foreground', '#9C009C'), 'to': 12}, {'from': 5, 'data': ('background', '#7F0000'), 'to': 12}], 'HelloGoodbye'),

        ([{'from': 0, 'data': ('foreground', '#ff0000'), 'to': 5}, {'from': 0, 'data': ('background', '#00ff00'), 'to': 5}, {'from': 5, 'data': ('foreground', '#0000ff'), 'to': 12}], 'HelloGoodbye'),

        ([{'from': 0, 'data': ('foreground', '#777777'), 'to': 1}, {'from': 1, 'data': ('foreground', '#00CCCC'), 'to': 6}, {'from': 6, 'data': ('foreground', '#777777'), 'to': 7}], '(stuff)'),
        ]
    
    #"""

    #r = range(20000)    
    #for i in r:
    #    for test in tests:
    #        parse_mirc(test)
            
    """
    
    lines = [eval(line.strip()) for line in file("parse_mirc_torture_test.txt")]
    
    for r in range(100):
        for line in lines:
            parse_mirc(line)
            
    #""" 

    for i, (test, result) in enumerate(zip(tests, results)):
        if parse_mirc(test) != result:
            print i
            print test
            print parse_mirc(test)
            print result
            print

#import dis
#dis.dis(parse_mirc)
