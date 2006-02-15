import codecs

import gobject
import gtk
import pango

from conf import conf
import events
import parse_mirc
import ui
import urk

import servers
import editor

# This holds all tags for all windows ever
if 'tag_table' not in globals():
    tag_table = gtk.TextTagTable()
    
    link_tag = gtk.TextTag('link')
    link_tag.set_property('underline', pango.UNDERLINE_SINGLE)
    
    indent_tag = gtk.TextTag('indent')
    indent_tag.set_property('indent', -20)
    
    tag_table.add(link_tag)
    tag_table.add(indent_tag)

    #FIXME: MEH hates dictionaries, they remind him of the bad words
    styles = {}

def style_me(widget, style):
    widget.set_style(styles.get(style))

def set_style(widget, style):
    if style:
        # FIXME: find a better way...
        dummy = gtk.Label()
        dummy.set_style(None)
    
        def apply_style_fg(value):
            dummy.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(value))

        def apply_style_bg(value):
            dummy.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(value))

        def apply_style_font(value):
            dummy.modify_font(pango.FontDescription(value))
    
        style_functions = (
            ('fg', apply_style_fg),
            ('bg', apply_style_bg),
            ('font', apply_style_font),
            )

        for name, f in style_functions:
            if name in style:
                f(style[name])

        style = dummy.rc_get_style()
    
    styles[widget] = style
    
def menu_from_list(alist):
    while alist and not alist[-1]:
        alist.pop(-1)

    last = None
    for item in alist:
        if item != last:
            if item:
                if len(item) == 2:
                    name, function = item
                    
                    menuitem = gtk.ImageMenuItem(name)
                    
                elif len(item) == 3:
                    name, stock_id, function = item
                    
                    menuitem = gtk.ImageMenuItem(stock_id)
                    
                if isinstance(function, list):
                    submenu = gtk.Menu()
                    for subitem in menu_from_list(function):
                        submenu.append(subitem)
                    menuitem.set_submenu(submenu)

                else:
                    menuitem.connect("activate", lambda a, f: f(), function)

                yield menuitem

            else:
                yield gtk.SeparatorMenuItem()
                
        last = item

class Nicklist(gtk.TreeView):
    def click(self, widget, event):
        if event.button == 3:
            x, y = event.get_coords()
            x, y = int(x), int(y)
    
            (data,), path, x, y = self.get_path_at_pos(x, y)
        
            c_data = events.data(
                        window=self.win,
                        data=self[data],
                        menu=[]
                        )
        
            events.trigger("ListRightClick", c_data)
            
            if c_data.menu:
                menu = gtk.Menu()
                for item in menu_from_list(c_data.menu):
                    menu.append(item)
                menu.show_all()
                menu.popup(None, None, None, event.button, event.time)
    
    def __getitem__(self, pos):
        return self.get_model()[pos][0]
        
    def __setitem__(self, pos, item):
        self.get_model()[pos] = [item]
    
    def __len__(self):
        return len(self.get_model())
    
    def index(self, item):
        for i, x in enumerate(self):
            if x == item:
                return i
                
        return -1
        
    def append(self, item):
        self.get_model().append([item])
 
    def insert(self, pos, item):
        self.get_model().insert(pos, [item])
        
    def extend(self, items):
        for i in items:
            self.append(i)

    def remove(self, item):
        self.get_model().remove(
            self.get_model().iter_nth_child(None, self.index(item))
            )
    
    def clear(self):
        self.get_model().clear()
        
    def __iter__(self):
        return (r[0] for r in self.get_model())

    def __init__(self, window):
        self.win = window
        
        gtk.TreeView.__init__(self, gtk.ListStore(str))

        self.set_headers_visible(False)

        self.insert_column_with_attributes(
            0, "", gtk.CellRendererText(), text=0
            )
            
        self.get_column(0).set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        self.set_property("fixed-height-mode", True)
        self.connect("button-press-event", self.click)
        
        style_me(self, "nicklist")

# Label used to display/edit your current nick on a network
class NickEdit(gtk.EventBox):
    def update(self, nick=None):
        nick = nick or self.win.network.me
            
        self.label.set_text(nick)
        self.edit.set_text(nick)
    
    def toggle(self, *args):
        if self.mode == "edit":
            self.mode = "show"
        
            self.remove(self.edit)
            self.add(self.label)
            
            self.win.input.grab_focus()

        else:
            self.mode = "edit"
            
            self.edit.set_text(self.label.get_text())
        
            self.remove(self.label)
            self.add(self.edit)
            
            self.edit.grab_focus()

    def __init__(self, window):
        gtk.EventBox.__init__(self)
        
        self.mode = "show"
        self.win = window

        self.label = gtk.Label()
        self.label.set_padding(5, 0)
        self.add(self.label)
        
        self.edit = gtk.Entry()
        self.edit.show()

        def nick_change(*args):
            oldnick, newnick = self.label.get_text(), self.edit.get_text()
        
            if newnick and newnick != oldnick:
                events.run('nick %s' % newnick, self.win, self.win.network)

            self.win.input.grab_focus()
                
        self.edit.connect("activate", nick_change)

        self.connect("button-press-event", self.toggle)
        self.edit.connect("focus-out-event", self.toggle)
        
        self.update()
        
        def set_cursor(widget, *args):
            self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.XTERM))
        
        self.connect("realize", set_cursor)

# The entry which you type in to send messages        
class TextInput(gtk.Entry):
    # Generates an input event
    def entered_text(self, *args):
        for line in self.text.splitlines():
            if line:
                e_data = events.data(
                            window=self.win,
                            text=line,
                            network=self.win.network
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
    text = property(gtk.Entry.get_text, gtk.Entry.set_text)
    cursor = property(gtk.Entry.get_position, gtk.Entry.set_position)
    selection = property(gtk.Entry.get_selection_bounds, _set_selection)
    
    def insert(self, text):
        self.do_insert_at_cursor(self, text)
    
    #hack to stop it selecting the text when we focus
    def do_grab_focus(self):
        temp = self.text, (self.selection or (self.cursor,)*2)
        self.text = ''
        gtk.Entry.do_grab_focus(self)
        self.text, self.selection = temp

    def __init__(self, window):
        gtk.Entry.__init__(self)
        
        self.win = window
        
        up = gtk.gdk.keyval_from_name("Up")
        down = gtk.gdk.keyval_from_name("Down")
        tab = gtk.gdk.keyval_from_name("Tab")
        
        def key_event(widget, event, event_type):
            key = ''
            for k, c in ((gtk.gdk.CONTROL_MASK, '^'),
                            (gtk.gdk.SHIFT_MASK, '+'),
                            (gtk.gdk.MOD1_MASK, '!')):
                if event.state & k:
                    key += c
            
            key += gtk.gdk.keyval_name(event.keyval)
            
            events.trigger(
                event_type,
                events.data(key=key, string=event.string, window=self.win)
                )
        
            return event.keyval in (up, down, tab)
        
        self.connect('key-press-event', key_event, 'KeyPress')
        self.connect_after('key-press-event', lambda *a: True)

        self.connect('activate', self.entered_text)

gobject.type_register(TextInput)

def prop_to_gtk(prop, val):
    if val == parse_mirc.BOLD:
        val = pango.WEIGHT_BOLD

    elif val == parse_mirc.UNDERLINE:
        val = pango.UNDERLINE_SINGLE
        
    return prop, val
        
def word_from_pos(text, pos):
    if text[pos] == ' ':
        return ' ', pos, pos+1

    else:
        fr = text[:pos].split(" ")[-1]
        to = text[pos:].split(" ")[0]

        return fr + to, pos - len(fr), pos + len(to)
 
def get_iter_at_coords(view, x, y):
    return view.get_iter_at_location(
        *view.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT, int(x), int(y))
        )

def get_event_at_iter(view, iter):
    buffer = view.get_buffer()
        
    line_strt = buffer.get_iter_at_line(iter.get_line())
    line_end = line_strt.copy()
    line_end.forward_lines(1)
    
    pos = iter.get_line_offset()
    
    #Caveat: text must be a unicode string, not utf-8 encoded; otherwise our
    # offsets will be off when we use anything outside 7-bit ascii
    #gtk.TextIter.get_text returns unicode but gtk.TextBuffer.get_text does not
    text = line_strt.get_text(line_end).rstrip("\n")
    
    word, fr, to = word_from_pos(text, pos)
    
    return events.data(
                window=view.win, pos=pos, text=text,
                target=word, target_fr=fr, target_to=to,
                )

class TextOutput(gtk.TextView):
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
    
    def get_ymax(self):
        buffer = self.get_buffer()
        return sum(self.get_line_yrange(self.get_buffer().get_end_iter())) - self.height
    
    def get_height(self):
        return self.get_visible_rect().height
    
    y = property(get_y, set_y)
    ymax = property(get_ymax)
    height = property(get_height)
    
    # the unknowing print weird things to our text widget function
    def write(self, text, activity_type, line_ending='\n'):
        if not isinstance(text, unicode):
            try:
                text = codecs.utf_8_decode(text)[0]
            except:
                text = codecs.latin_1_decode(text)[0]
        tag_data, text = parse_mirc.parse_mirc(text)

        buffer = self.get_buffer()
        
        cc = buffer.get_char_count()

        buffer.insert(buffer.get_end_iter(), text + line_ending)
        
        buffer.apply_tag_by_name(
            'indent', 
            buffer.get_iter_at_offset(cc),
            buffer.get_end_iter()
            )

        for tag_props, start_i, end_i in tag_data:
            tag_props = tuple(prop_to_gtk(*p) for p in tag_props)
            tag_name = str(hash(tag_props))
                 
            if not tag_table.lookup(tag_name):
                buffer.create_tag(tag_name, **dict(tag_props))
                
            buffer.apply_tag_by_name(
                tag_name, 
                buffer.get_iter_at_offset(start_i + cc),
                buffer.get_iter_at_offset(end_i + cc)
                )
    
    def popup(self, widget, menu):       
        hover_iter = get_iter_at_coords(self, *self.hover_coords)
        
        menuitems = []
        if not hover_iter.ends_line():
            c_data = get_event_at_iter(self, hover_iter)
            c_data.menu = []
            
            events.trigger("RightClick", c_data)
            
            menuitems = c_data.menu
            
        if not menuitems:
            data = events.data(menu=[])
            events.trigger("MainMenu", data)
            
            menuitems = data.menu

        for child in menu.get_children():
            menu.remove(child)
        
        for item in menu_from_list(menuitems):
            menu.append(item)
            
        menu.show_all()
    
    def mousedown(self, widget, event):
        if event.button == 3:
            self.hover_coords = event.get_coords()
    
    def mouseup(self, widget, event):
        if event.button == 1 and not self.get_buffer().get_selection_bounds():
            hover_iter = get_iter_at_coords(self, event.x, event.y)
        
            if not hover_iter.ends_line():
                c_data = get_event_at_iter(self, hover_iter)

                events.trigger("Click", c_data)
                
            if self.is_focus():
                self.win.focus()

    def clear_hover(self, *args):
        buffer = self.get_buffer()
    
        for fr, to in self.linking:
            buffer.remove_tag_by_name(
                "link", 
                buffer.get_iter_at_mark(fr), 
                buffer.get_iter_at_mark(to)
                )
        
        self.linking = set()
        self.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(None)

    def hover(self, widget, event):
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
                        gtk.TEXT_WINDOW_TEXT
                        ).set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND2))

        self.get_pointer()

    def __init__(self, window):
        gtk.TextView.__init__(self, gtk.TextBuffer(tag_table))
        
        self.win = window
        
        self.set_wrap_mode(gtk.WRAP_WORD_CHAR)
        self.set_editable(False)
        self.set_cursor_visible(False)
        
        self.set_pixels_above_lines(1)
        
        self.set_property("left-margin", 3)
        self.set_property("right-margin", 3)

        self.linking = set()

        self.add_events(gtk.gdk.POINTER_MOTION_HINT_MASK)
        self.add_events(gtk.gdk.LEAVE_NOTIFY_MASK)

        self.connect("motion-notify-event", self.hover)
        self.connect("button-press-event", self.mousedown)
        self.connect("button-release-event", self.mouseup)
        self.connect("leave-notify-event", self.clear_hover)
          
        self.hover_coords = 0, 0
        
        self.connect("populate-popup", self.popup)
        
        self.set_size_request(0, -1)

        self.to_scroll = True
        self.scroller = gtk.Adjustment()

        def scroll(*args):
            if self.to_scroll:
                self.scroller.value = self.scroller.upper - self.scroller.page_size

        self.connect("size-allocate", scroll)
        
        def connect_adjustments(self, _adj, vadj):
            if vadj:
                def set_scroll(adj):
                    self.to_scroll = adj.value + adj.page_size >= adj.upper

                vadj.connect("value-changed", set_scroll)
                
            self.scroller = vadj

        self.connect("set-scroll-adjustments", connect_adjustments)

        def set_cursor(widget):
            self.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(None)      

        self.connect("realize", set_cursor)
        
        style_me(self, "view")

class WindowLabel(gtk.EventBox):
    def update(self):
        title = self.win.title
        title = title.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        
        for a_type in sorted(ui.activity_markup, reverse=True):
            if self.win.activity == a_type:
                title = ui.activity_markup[a_type] % title
                break
            
        self.label.set_markup(title)

    def tab_popup(self, widget, event):
        if event.button == 3: # right click
            c_data = events.data(window=self.win, menu=[])
            events.trigger("WindowMenu", c_data)

            c_data.menu += [
                None,
                ("Close", gtk.STOCK_CLOSE, self.win.close),
                ]
            
            menu = gtk.Menu()
            for item in menu_from_list(c_data.menu):
                menu.append(item)
            menu.show_all()
            menu.popup(None, None, None, event.button, event.time)

    def __init__(self, window):
        gtk.EventBox.__init__(self)

        self.win = window
        self.connect("button-press-event", self.tab_popup)
        
        self.label = gtk.Label()        
        self.add(self.label)

        self.update()
        self.show_all()
        
class FindBox(gtk.HBox):
    def remove(self, *args):
        self.parent.remove(self)
        self.win.focus()

    def clicked(self, *args):
        button = args[-1]
    
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
    
        if button == self.up:
            cursor = cursor_iter.backward_search(
                text, gtk.TEXT_SEARCH_VISIBLE_ONLY
                )
        elif button == self.down:
            cursor = cursor_iter.forward_search(
                text, gtk.TEXT_SEARCH_VISIBLE_ONLY
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
        gtk.HBox.__init__(self)
        
        self.win = window

        self.up = gtk.Button(stock='gtk-go-up')
        self.down = gtk.Button(stock='gtk-go-down')
        
        self.up.connect('clicked', self.clicked)
        self.down.connect('clicked', self.clicked)
        
        self.up.props.can_focus = False
        self.down.props.can_focus = False
        
        self.textbox = gtk.Entry()
        
        self.textbox.connect('focus-out-event', self.remove)
        self.textbox.connect('activate', self.clicked, self.up)
                
        self.pack_start(gtk.Label('Find:'), expand=False)
        self.pack_start(self.textbox)

        self.pack_start(self.up, expand=False)
        self.pack_start(self.down, expand=False)

        self.show_all()

class UrkUITabs(gtk.Window):
    def set_title(self, title=None):
        if title is None:
            w = self.get_active()
            
            if w.role != ui.StatusWindow:
                if w.network.status:
                    server = w.network.server
                else:
                    server = "[%s]" % w.network.server
                    
                title = "%s - %s - %s" % (w.network.me, server, w.title)
            else:
                title = "%s - %s" % (w.network.me, w.title)
        
        gtk.Window.set_title(self, "%s - urk" % title)

    def __iter__(self):
        return iter(self.tabs.get_children())

    def exit(self, *args):
        events.trigger("Exit")
        gtk.main_level() and gtk.main_quit()
        
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

    def menu(self):
        def add_defaults_to_menu(e):
            e.menu += [('Servers', gtk.STOCK_CONNECT, servers.main)]
            e.menu += [('Editor', editor.main)]

        events.register('MainMenu', 'on', add_defaults_to_menu, 'ui')

        def build_urk_menu(*args):
            data = events.data(menu=[])
            events.trigger("MainMenu", data)

            menu = gtk.Menu()
            for item in menu_from_list(data.menu):
                menu.append(item)
            menu.show_all()
            
            urk_menu.set_submenu(menu)
        
        urk_menu = gtk.MenuItem("urk")
        urk_menu.connect("button-press-event", build_urk_menu)    
        help_menu = gtk.MenuItem("Help")
        
        help_menu.set_submenu(gtk.Menu())
        about_item = gtk.ImageMenuItem("gtk-about")
        about_item.connect("activate", ui.urk_about)

        help_menu.get_submenu().append(about_item)
        
        menu = gtk.MenuBar()
        menu.append(urk_menu)
        menu.append(help_menu)
        
        return menu
    
    def __init__(self):
        # threading stuff
        gtk.gdk.threads_init()
        
        gtk.Window.__init__(self)
        
        try:
            self.set_icon(
                gtk.gdk.pixbuf_new_from_file(urk.path("urk_icon.svg"))
                )
        except:
            pass

        self.connect("delete_event", self.exit)

        # layout
        xy = conf.get("xy", (-1, -1))
        wh = conf.get("wh", (500, 500))

        self.move(*xy)
        self.set_default_size(*wh)
        
        def save_xywh(*args):
            conf["xy"] = self.get_position()
            conf["wh"] = self.get_size()
        self.connect("configure_event", save_xywh)
        
        self.tabs = gtk.Notebook()
        
        self.tabs.set_property(
            "tab-pos", 
            conf.get("ui-gtk/tab-pos", gtk.POS_BOTTOM)
            )

        self.tabs.set_scrollable(True)
        self.tabs.set_property("can-focus", False)

        def window_change(notebook, wptr, page_num):
            events.trigger("Active", notebook.get_nth_page(page_num))
            
        self.tabs.connect("switch-page", window_change)
        
        menu = self.menu()

        box = gtk.VBox(False)
        if conf.get('ui-gtk/show_menubar', True):
            box.pack_start(menu, expand=False)
        box.pack_end(self.tabs)

        gtk.Window.add(self, box)
        self.show_all()
