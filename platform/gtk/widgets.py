import codecs

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango

from conf import conf
import events
import parse_mirc
import urk
import windows

def about(*args):
    about = Gtk.AboutDialog()
    
    about.set_name(urk.name+" (GTK+ Frontend)")
    about.set_version(".".join(str(x) for x in urk.version))
    about.set_copyright("Copyright \xc2\xa9 %s" % urk.copyright)
    about.set_website(urk.website)
    about.set_authors(urk.authors)
    
    def on_response(*args):
        about.destroy()
    
    about.connect("response", on_response)
    
    about.show_all()

# Window activity Constants
HILIT = 'h'
TEXT ='t'
EVENT = 'e'

ACTIVITY_MARKUP = {
    HILIT: "<span style='italic' foreground='#00F'>%s</span>",
    TEXT: "<span foreground='#ca0000'>%s</span>",
    EVENT: "<span foreground='#363'>%s</span>",
    }

# This holds all tags for all windows ever
tag_table = Gtk.TextTagTable()

link_tag = Gtk.TextTag.new('link')
link_tag.set_property('underline', Pango.Underline.SINGLE)

indent_tag = Gtk.TextTag.new('indent')
indent_tag.set_property('indent', -20)

tag_table.add(link_tag)
tag_table.add(indent_tag)

#FIXME: MEH hates dictionaries, they remind him of the bad words
styles = {}

def style_me(widget, style):
    widget.set_style(styles.get(style))

def set_style(widget_name, style):
    if style:
        # FIXME: find a better way...
        dummy = Gtk.Label()
        dummy.set_style(None)
    
        def apply_style_fg(value):
            dummy.modify_text(Gtk.StateType.NORMAL, Gdk.color_parse(value))

        def apply_style_bg(value):
            dummy.modify_base(Gtk.StateType.NORMAL, Gdk.color_parse(value))

        def apply_style_font(value):
            dummy.modify_font(Pango.FontDescription(value))
    
        style_functions = (
            ('fg', apply_style_fg),
            ('bg', apply_style_bg),
            ('font', apply_style_font),
            )

        for name, f in style_functions:
            if name in style:
                f(style[name])

        style = dummy.rc_get_style()
    else:
        style = None
    
    styles[widget_name] = style
    
def menu_from_list(alist):
    while alist and not alist[-1]:
        alist.pop(-1)

    last = None
    for item in alist:
        if item != last:
            if item:
                if len(item) == 2:
                    name, function = item
                    
                    menuitem = Gtk.ImageMenuItem(name)
                    
                elif len(item) == 3:
                    name, stock_id, function = item
                    
                    if isinstance(stock_id, bool):
                        menuitem = Gtk.CheckMenuItem(name)
                        menuitem.set_active(stock_id)
                    else:
                        menuitem = Gtk.ImageMenuItem(stock_id)
                    
                if isinstance(function, list):
                    submenu = Gtk.Menu()
                    for subitem in menu_from_list(function):
                        submenu.append(subitem)
                    menuitem.set_submenu(submenu)

                else:
                    menuitem.connect("activate", lambda a, f: f(), function)

                yield menuitem

            else:
                yield Gtk.SeparatorMenuItem()
                
        last = item

class Nicklist(Gtk.TreeView):
    def click(self, event):
        if event.button == 3:
            x, y = event.get_coords()
    
            (data,), path, x, y = self.get_path_at_pos(int(x), int(y))
        
            c_data = events.data(window=self.win, data=self[data], menu=[])
        
            events.trigger("ListRightClick", c_data)
            
            if c_data.menu:
                menu = Gtk.Menu()
                for item in menu_from_list(c_data.menu):
                    menu.append(item)
                menu.show_all()
                menu.popup(None, None, None, event.button, event.time)
        
        elif event.button == 1 and event.type == Gdk._2BUTTON_PRESS:
            x, y = event.get_coords()
    
            (data,), path, x, y = self.get_path_at_pos(int(x), int(y))
        
            events.trigger("ListDoubleClick", window=self.win, target=self[data])
        
    def __getitem__(self, pos):
        return self.get_model()[pos][0]
        
    def __setitem__(self, pos, name_markup):
        realname, markedupname, sortkey = name_markup
    
        self.get_model()[pos] = realname, markedupname, sortkey

    def __len__(self):
        return len(self.get_model())
    
    def index(self, item):
        for i, x in enumerate(self):
            if x == item:
                return i
                
        return -1
        
    def append(self, realname, markedupname, sortkey):
        self.get_model().append((realname, markedupname, sortkey))
 
    def insert(self, pos, realname, markedupname, sortkey):
        self.get_model().insert(pos, (realname, markedupname, sortkey))
        
    def replace(self, names):
        self.set_model(Gtk.ListStore(str, str, str))
        
        self.insert_column_with_attributes(
            0, '', Gtk.CellRendererText(), markup=1
            ).set_sizing(Gtk.TreeViewColumnSizing.FIXED)

        for name in names:
            self.append(*name)
        
        self.get_model().set_sort_column_id(2, Gtk.SortType.ASCENDING)

    def remove(self, realname):
        index = self.index(realname)
        
        if index == -1:
            raise ValueError

        self.get_model().remove(self.get_model().iter_nth_child(None, index))
    
    def clear(self):
        self.get_model().clear()
        
    def __iter__(self):
        return (r[0] for r in self.get_model())

    def on_keypress(self, event):
        if event.string and not (event.get_state() & (Gdk.ModifierType.CONTROL_MASK|Gdk.ModifierType.MOD1_MASK|Gdk.ModifierType.MOD2_MASK|Gdk.ModifierType.MOD3_MASK|Gdk.ModifierType.MOD4_MASK|Gdk.ModifierType.MOD5_MASK)):
            #redirect character input to the TextInput
            new_event = event.copy()
            try:
                new_event.window = self.win.input.window
            except AttributeError:
                # this window has no TextInput
                return False
            self.win.input.grab_focus()
            self.win.input.event(new_event)
            return True

    def __init__(self, window):
        self.win = window
        
        GObject.GObject.__init__(self)
        
        self.replace(())

        self.set_headers_visible(False)
        self.set_property("fixed-height-mode", True)
        self.connect("button-press-event", Nicklist.click)
        self.connect_after("button-release-event", lambda *a: True)
        self.connect("key-press-event", Nicklist.on_keypress)
   
        style_me(self, "nicklist")

# Label used to display/edit your current nick on a network
class NickEditor(Gtk.EventBox):
    def nick_change(self, entry):
        oldnick, newnick = self.label.get_text(), entry.get_text()
        
        if newnick and newnick != oldnick:
            events.run('nick %s' % newnick, self.win, self.win.network)

        self.win.input.grab_focus()

    def update(self, nick=None):
        self.label.set_text(nick or self.win.network.me)
    
    def to_edit_mode(self, widget, event):
        if self.label not in self.get_children():
            return

        if getattr(event, 'button', None) == 3:
            c_data = events.data(window=self.win, menu=[])
            events.trigger("NickEditMenu", c_data)

            if c_data.menu:
                menu = Gtk.Menu()
                for item in menu_from_list(c_data.menu):
                    menu.append(item)
                menu.show_all()
                menu.popup(None, None, None, event.button, event.time)
        
        else:
            entry = Gtk.Entry()
            entry.set_text(self.label.get_text())
            entry.connect('activate', self.nick_change)
            entry.connect('focus-out-event', self.to_show_mode)

            self.remove(self.label)
            self.add(entry)
            self.window.set_cursor(None)
                
            entry.show()
            entry.grab_focus()
    
    def to_show_mode(self, widget, event):
        self.remove(widget)
        self.add(self.label)
        self.win.input.grab_focus()
        self.window.set_cursor(Gdk.Cursor.new(Gdk.XTERM))

    def __init__(self, window):
        GObject.GObject.__init__(self)

        self.win = window

        self.label = Gtk.Label()
        self.label.set_padding(5, 0)
        self.add(self.label)

        self.connect("button-press-event", self.to_edit_mode)
        
        self.update()

        self.connect(
            "realize", 
            lambda *a: self.window.set_cursor(Gdk.Cursor.new(Gdk.XTERM))
            )

# The entry which you type in to send messages        
class TextInput(Gtk.Entry):
    # Generates an input event
    def entered_text(self, ctrl):
        #FIXME: move this logic into Window
        for line in self.text.splitlines():
            if line:
                e_data = events.data(
                            window=self.win, network=self.win.network,
                            text=line, ctrl=ctrl
                            )
                events.trigger('Input', e_data)
                
                if not e_data.done:
                    events.run(line, self.win, self.win.network)
        
        self.text = ''
    
    def _set_selection(self, s):
        if s:
            self.select_region(*s)
        else:
            self.select_region(self.cursor, self.cursor)

    #some nice toys for the scriptors
    text = property(Gtk.Entry.get_text, Gtk.Entry.set_text)
    cursor = property(Gtk.Entry.get_position, Gtk.Entry.set_position)
    selection = property(Gtk.Entry.get_selection_bounds, _set_selection)
    
    def insert(self, text):
        self.do_insert_at_cursor(self, text)
    
    #hack to stop it selecting the text when we focus
    def do_grab_focus(self):
        temp = self.text, (self.selection or (self.cursor,)*2)
        self.text = ''
        Gtk.Entry.do_grab_focus(self)
        self.text, self.selection = temp

    def keypress(self, event):
        keychar = (
            (Gdk.ModifierType.CONTROL_MASK, '^'),
            (Gdk.ModifierType.SHIFT_MASK, '+'),
            (Gdk.ModifierType.MOD1_MASK, '!')
            )

        key = ''
        for keymod, char in keychar:
            # we make this an int, because otherwise it leaks
            if int(event.get_state()) & keymod:
                key += char
        key += Gdk.keyval_name(event.keyval)

        events.trigger('KeyPress', key=key, string=event.string, window=self.win)

        if key == "^Return":
            self.entered_text(True)
        
        up = Gdk.keyval_from_name("Up")
        down = Gdk.keyval_from_name("Down")
        tab = Gdk.keyval_from_name("Tab")

        return event.keyval in (up, down, tab)
    
    def __init__(self, window):
        GObject.GObject.__init__(self)
        
        self.win = window

        # we don't want key events to propogate so we stop them in connect_after
        self.connect('key-press-event', TextInput.keypress)
        self.connect_after('key-press-event', lambda *a: True)
        
        self.connect('activate', TextInput.entered_text, False)

GObject.type_register(TextInput)

def prop_to_gtk(textview, (prop, val)):
    if val == parse_mirc.BOLD:
        val = Pango.Weight.BOLD

    elif val == parse_mirc.UNDERLINE:
        val = Pango.Underline.SINGLE
        
    return {prop: val}
        
def word_from_pos(text, pos):
    if text[pos] == ' ':
        return ' ', pos, pos+1

    else:
        fr = text[:pos].split(" ")[-1]
        to = text[pos:].split(" ")[0]

        return fr + to, pos - len(fr), pos + len(to)
 
def get_iter_at_coords(view, x, y):
    return view.get_iter_at_location(
        *view.window_to_buffer_coords(Gtk.TextWindowType.TEXT, int(x), int(y))
        )

def get_event_at_iter(view, iter):
    buffer = view.get_buffer()
        
    line_strt = buffer.get_iter_at_line(iter.get_line())
    line_end = line_strt.copy()
    line_end.forward_lines(1)
    
    pos = iter.get_line_offset()
    
    #Caveat: text must be a unicode string, not utf-8 encoded; otherwise our
    # offsets will be off when we use anything outside 7-bit ascii
    #Gtk.TextIter.get_text returns unicode but Gtk.TextBuffer.get_text does not
    text = line_strt.get_text(line_end).rstrip("\n")
    
    word, fr, to = word_from_pos(text, pos)
    
    return events.data(
                window=view.win, pos=pos, text=text,
                target=word, target_fr=fr, target_to=to,
                )

class TextOutput(Gtk.TextView):
    def copy(self):
        startend = self.get_buffer().get_selection_bounds()

        tagsandtext = []
        if startend:
            start, end = startend
            
            while not start.equal(end):
                tags_at_iter = {}
                for tag in start.get_tags():        
                    try:
                        tagname, tagval = eval(tag.get_property('name'))
                        tags_at_iter[tagname] = tagval
                    except NameError:
                        continue

                tagsandtext.append((dict(tags_at_iter), start.get_char()))
                start.forward_char()

        text = parse_mirc.unparse_mirc(tagsandtext)
        
        Gtk.clipboard_get(Gdk.SELECTION_CLIPBOARD).set_text(text)
        Gtk.clipboard_get(Gdk.SELECTION_PRIMARY).set_text(text)

        return text

    def clear(self):
        self.get_buffer().set_text('')
    
    def get_y(self):
        rect = self.get_visible_rect()
        return rect.y
    
    def set_y(self,y):
        iter = self.get_iter_at_location(0, y)
        if self.get_iter_location(iter).y < y:
            self.forward_display_line(iter)
        yalign = float(self.get_iter_location(iter).y-y)/self.height
        self.scroll_to_iter(iter, 0, True, 0, yalign)
        
        self.check_autoscroll()
    
    def get_ymax(self):
        buffer = self.get_buffer()
        return sum(self.get_line_yrange(buffer.get_end_iter())) - self.height
    
    def get_height(self):
        return self.get_visible_rect().height
    
    y = property(get_y, set_y)
    ymax = property(get_ymax)
    height = property(get_height)
    
    # the unknowing print weird things to our text widget function
    def write(self, text, line_ending='\n', fg=None):
        if not isinstance(text, unicode):
            try:
                text = codecs.utf_8_decode(text)[0]
            except:
                text = codecs.latin_1_decode(text)[0]
        tags, text = parse_mirc.parse_mirc(text)

        if fg:
            tags.append({'data': ("foreground", isinstance(fg, basestring) and ('#%s'%fg) or parse_mirc.get_mirc_color(fg)), 'from': 0, 'to': len(text)})

        buffer = self.get_buffer()
        
        cc = buffer.get_char_count()

        buffer.insert_with_tags_by_name(
            buffer.get_end_iter(),
            text + line_ending,
            'indent'
            )

        for tag in tags:
            tag_name = str(tag['data'])
   
            if not tag_table.lookup(tag_name):
                buffer.create_tag(tag_name, **prop_to_gtk(self, tag['data']))

            buffer.apply_tag_by_name(
                tag_name, 
                buffer.get_iter_at_offset(tag['from'] + cc),
                buffer.get_iter_at_offset(tag['to'] + cc)
                )
    
    def popup(self, menu):    
        hover_iter = get_iter_at_coords(self, *self.hover_coords)
       
        menuitems = []
        if not hover_iter.ends_line():
            c_data = get_event_at_iter(self, hover_iter)
            c_data.menu = []
            
            events.trigger("RightClick", c_data)
            
            menuitems = c_data.menu
            
        if not menuitems:
            c_data = events.data(menu=[])
            events.trigger("MainMenu", c_data)
            
            menuitems = c_data.menu

        for child in menu.get_children():
            menu.remove(child)
        
        for item in menu_from_list(menuitems):
            menu.append(item)
            
        menu.show_all()
    
    def mousedown(self, event):
        if event.button == 3:
            self.hover_coords = event.get_coords()
    
    def mouseup(self, event):
        if not self.get_buffer().get_selection_bounds():
            if event.button == 1:
                hover_iter = get_iter_at_coords(self, event.x, event.y)
            
                if not hover_iter.ends_line():
                    c_data = get_event_at_iter(self, hover_iter)

                    events.trigger("Click", c_data)
                
            if self.is_focus():
                self.win.focus()

    def clear_hover(self, _event=None):
        buffer = self.get_buffer()
    
        for fr, to in self.linking:
            buffer.remove_tag_by_name(
                "link", 
                buffer.get_iter_at_mark(fr), 
                buffer.get_iter_at_mark(to)
                )
        
        self.linking = set()
        self.get_window(Gtk.TextWindowType.TEXT).set_cursor(None)

    def hover(self, event):
        if self.linking:
            self.clear_hover()

        hover_iter = get_iter_at_coords(self, event.x, event.y)

        if not hover_iter.ends_line():        
            h_data = get_event_at_iter(self, hover_iter)
            h_data.tolink = set()

            events.trigger("Hover", h_data)
            
            if h_data.tolink:
                buffer = self.get_buffer()
            
                offset = buffer.get_iter_at_line(
                            hover_iter.get_line()
                            ).get_offset()
                                  
                for fr, to in h_data.tolink:
                    fr = buffer.get_iter_at_offset(offset + fr)
                    to = buffer.get_iter_at_offset(offset + to)
                    
                    buffer.apply_tag_by_name("link", fr, to)
                    
                    self.linking.add(
                        (buffer.create_mark(None, fr), 
                            buffer.create_mark(None, to))
                        )
                        
                    self.get_window(
                        Gtk.TextWindowType.TEXT
                        ).set_cursor(Gdk.Cursor.new(Gdk.HAND2))
        
        self.get_pointer()

    def scroll(self, _allocation=None):
        if self.autoscroll:
            def do_scroll():
                self.scroller.value = self.scroller.upper - self.scroller.page_size
                self._scrolling = False
            
            if not self._scrolling:
                self._scrolling = GObject.idle_add(do_scroll)
    
    def check_autoscroll(self, *args):
        def set_to_scroll():
            self.autoscroll = self.scroller.value + self.scroller.page_size >= self.scroller.upper
            
        GObject.idle_add(set_to_scroll)

    def on_keypress(self, event):
        if event.string and not (event.get_state() & (Gdk.ModifierType.CONTROL_MASK|Gdk.ModifierType.MOD1_MASK|Gdk.ModifierType.MOD2_MASK|Gdk.ModifierType.MOD3_MASK|Gdk.ModifierType.MOD4_MASK|Gdk.ModifierType.MOD5_MASK)):
            #redirect character input to the TextInput
            new_event = event.copy()
            try:
                new_event.window = self.win.input.window
            except AttributeError:
                # this window has no TextInput
                return False
            self.win.input.grab_focus()
            self.win.input.event(new_event)
            return True

    def __init__(self, window, buffer=None):
        GObject.GObject.__init__(self)
        
        if not buffer:
            buffer = Gtk.TextBuffer.new(tag_table)

        self.set_buffer(buffer)
        
        self.win = window
        
        self.set_size_request(0, -1)
        
        self.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.set_editable(False)
        self.set_cursor_visible(False)

        self.set_property("left-margin", 3)
        self.set_property("right-margin", 3)

        self.linking = set()

        self.add_events(Gdk.EventMask.POINTER_MOTION_HINT_MASK)
        self.add_events(Gdk.EventMask.LEAVE_NOTIFY_MASK)

        self.connect('populate-popup', TextOutput.popup)
        self.connect('motion-notify-event', TextOutput.hover)
        self.connect('button-press-event', TextOutput.mousedown)
        self.connect('button-release-event', TextOutput.mouseup)
        self.connect_after('button-release-event', lambda *a: True)
        self.connect('leave-notify-event', TextOutput.clear_hover)
        self.connect('key-press-event', TextOutput.on_keypress)
        
        self.hover_coords = 0, 0

        self.autoscroll = True
        self._scrolling = False
        self.scroller = Gtk.Adjustment()

        def setup_scroll(self, _adj, vadj):
            self.scroller = vadj

            if vadj:
                def set_scroll(adj):
                    self.autoscroll = adj.value + adj.page_size >= adj.upper
    
                vadj.connect("value-changed", set_scroll)

        # TODO: reimplement auto window scroll in GTK3
        #self.connect("set-scroll-adjustments", setup_scroll)
        #self.connect("size-allocate", TextOutput.scroll)

        def set_cursor(widget):
            self.get_window(Gtk.TextWindowType.TEXT).set_cursor(None)      

        self.connect("realize", set_cursor)
        
        style_me(self, "view")

class WindowLabel(Gtk.EventBox):
    def update(self):
        title = self.win.get_title()
        
        for escapes in (('&','&amp;'), ('<','&lt;'), ('>','&gt;')):
            title = title.replace(*escapes)

        for a_type in (HILIT, TEXT, EVENT):
            if a_type in self.win.activity:
                title = ACTIVITY_MARKUP[a_type] % title
                break
            
        self.label.set_markup(title)

    def tab_popup(self, event):
        if event.button == 3: # right click
            c_data = events.data(window=self.win, menu=[])
            events.trigger("WindowMenu", c_data)

            c_data.menu += [
                None,
                ("Close", Gtk.STOCK_CLOSE, self.win.close),
                ]
            
            menu = Gtk.Menu()
            for item in menu_from_list(c_data.menu):
                menu.append(item)
            menu.show_all()
            menu.popup(None, None, None, event.button, event.time)

    def __init__(self, window):
        GObject.GObject.__init__(self)

        self.win = window
        self.connect("button-press-event", WindowLabel.tab_popup)
        
        self.label = Gtk.Label()        
        self.add(self.label)

        self.update()
        self.show_all()
        
class FindBox(Gtk.HBox):
    def remove(self, *args):
        self.parent.remove(self)
        self.win.focus()

    def clicked(self, button, search_down=False):
        text = self.textbox.get_text()
        
        if not text:
            return
        
        buffer = self.win.output.get_buffer()
        
        if buffer.get_selection_bounds():
            if button == self.down:
                _, cursor_iter = buffer.get_selection_bounds()
            else:
                cursor_iter, _ = buffer.get_selection_bounds()
        else:
           cursor_iter = buffer.get_end_iter()
    
        if search_down:
            cursor = cursor_iter.forward_search(
                text, Gtk.TextSearchFlags.VISIBLE_ONLY
                )
        else:
            cursor = cursor_iter.backward_search(
                text, Gtk.TextSearchFlags.VISIBLE_ONLY
                )
        
        if not cursor:
            return
        
        fr, to = cursor
        
        if button == self.up:
            buffer.place_cursor(fr)
            self.win.output.scroll_to_iter(fr, 0)
        elif button == self.down:
            buffer.place_cursor(to)
            self.win.output.scroll_to_iter(to, 0)
            
        buffer.select_range(*cursor)
        
        cursor_iter = buffer.get_iter_at_mark(buffer.get_insert())

    def __init__(self, window):
        GObject.GObject.__init__(self)
        
        self.win = window

        self.up = Gtk.Button(stock='gtk-go-up')
        self.down = Gtk.Button(stock='gtk-go-down')
        
        self.up.connect('clicked', self.clicked)
        self.down.connect('clicked', self.clicked, True)
        
        self.up.set_property('can_focus', False)
        self.down.set_property('can_focus', False)
        
        self.textbox = Gtk.Entry()
        
        self.textbox.connect('focus-out-event', self.remove)
        self.textbox.connect('activate', self.clicked)
                
        self.pack_start(Gtk.Label('Find:', True, True, 0), expand=False)
        self.pack_start(self.textbox, True, True, 0)

        self.pack_start(self.up, False, True, 0)
        self.pack_start(self.down, False, True, 0)

        self.show_all()

class UrkUITabs(Gtk.Window):
    def set_title(self, title=None):
        if title is None:
            title = self.get_active().get_toplevel_title()

        Gtk.Window.set_title(self, "%s - urk" % title)

    def __iter__(self):
        return iter(self.tabs.get_children())
    
    def __len__(self):
        return self.tabs.get_n_pages()
    
    def exit(self, *args):
        events.trigger("Exit")
        Gtk.main_level() and Gtk.main_quit()
        
    def get_active(self):
        return self.tabs.get_nth_page(self.tabs.get_current_page())
        
    def set_active(self, window):
        self.tabs.set_current_page(self.tabs.page_num(window))
        
    def add(self, window):
        for pos in reversed(range(self.tabs.get_n_pages())):
            if self.tabs.get_nth_page(pos).network == window.network:
                break
        else:
            pos = self.tabs.get_n_pages() - 1
 
        self.tabs.insert_page(window, WindowLabel(window), pos+1)   
        
    def remove(self, window):
        self.tabs.remove_page(self.tabs.page_num(window))
        
    def update(self, window):
        self.tabs.get_tab_label(window).update()
        
        if self.get_active() == window:
            self.set_title()
    
    def build_urk_menu(self, *args):
        data = events.data(menu=[])
        events.trigger("MainMenu", data)

        menu = self.urk_submenu
        for child in menu.get_children():
            menu.remove(child)
        for item in menu_from_list(data.menu):
            menu.append(item)
        menu.show_all()
    
    def build_menubar(self):
        self.urk_menu = Gtk.MenuItem("urk")
        self.urk_submenu = Gtk.Menu()
        self.urk_menu.set_submenu(self.urk_submenu)

        self.help_menu = Gtk.MenuItem("Help")
        self.help_submenu = Gtk.Menu()
        self.help_menu.set_submenu(self.help_submenu)
        
        about_item = Gtk.ImageMenuItem("gtk-about")
        about_item.connect("activate", about)
        self.help_submenu.append(about_item)
        
        self.menubar = Gtk.MenuBar()
        self.menubar.append(self.urk_menu)
        self.menubar.append(self.help_menu)
        
        self.urk_menu.connect('select', self.build_urk_menu)
        
        return self.menubar
    
    def __init__(self):
        GObject.GObject.__init__(self)
        
        try:
            self.set_icon(
                GdkPixbuf.Pixbuf.new_from_file(urk.path("urk_icon.svg"))
                )
        except:
            pass

        self.connect("delete-event", self.exit)

        # layout
        xy = conf.get("xy", (-1, -1))
        wh = conf.get("wh", (500, 500))
        maximized = conf.get("maximized", False)

        self.move(*xy)
        self.set_default_size(*wh)
        if maximized:
            self.maximize()

        self._saving = None
        def save_xywh(*args):
            if not self._saving:
                def save():
                    conf["xy"] = self.get_position()
                    conf["wh"] = self.get_size()
                    
                    self._saving = None
                    
                self._saving = GObject.timeout_add(200, save)

        self.connect("configure-event", save_xywh)
        
        def save_maximized(widget, event):
            if event.new_window_state & Gdk.WindowState.MAXIMIZED:
                conf["maximized"] = True
            else:
                conf["maximized"] = False
        
        self.connect("window-state-event", save_maximized)
        
        self.tabs = Gtk.Notebook()
        
        self.tabs.set_property(
            "tab-pos", 
            conf.get("ui-gtk/tab-pos", Gtk.PositionType.BOTTOM)
            )

        self.tabs.set_scrollable(True)
        self.tabs.set_property("can-focus", False)
        
        def super_window_change(self, event):
            if event.type == Gdk.EventType.FOCUS_CHANGE and event.in_:
                window = windows.manager.get_active()
            
                if window:
                    events.trigger('SuperActive', window=window)
                
        self.connect('event', super_window_change)

        def window_change(notebook, _wptr, page_num):
            events.trigger("Active", window=notebook.get_nth_page(page_num))
            
        self.tabs.connect("switch-page", window_change)
        
        menubar = self.build_menubar()

        box = Gtk.VBox(False)
        if conf.get('ui-gtk/show_menubar', True):
            box.pack_start(menubar, False, True, 0)
        box.pack_end(self.tabs, True, True, 0)

        Gtk.Window.add(self, box)
        self.show_all()
