import gtk
import pango

try:
    import gtksourceview
    GTK_SOURCE_VIEW = True
except:
    GTK_SOURCE_VIEW = False

import events
import ui
from conf import conf
import urk

class EditorWidget(gtk.VBox):
    def goto(self, line, offset):
        buffer = self.output.get_buffer()
                    
        cursor = buffer.get_iter_at_line_offset(
            line-1, offset
            )
        
        buffer.place_cursor(cursor)
        self.output.scroll_to_iter(cursor, 0)

    def load(self, text):
        buffer = self.output.get_buffer()

        if GTK_SOURCE_VIEW:
            buffer.begin_not_undoable_action()

        buffer.set_text(text)
        buffer.set_modified(False)

        if GTK_SOURCE_VIEW:
            buffer.end_not_undoable_action()
            
    def save(self):
        buffer = self.output.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter())

        self.output.get_buffer().set_modified(False)
        
        return text

    if GTK_SOURCE_VIEW:
        def edit_widget(self):
            self.output = gtksourceview.SourceView(gtksourceview.SourceBuffer())
            
            self.output.set_show_line_numbers(True)
            self.output.set_show_line_markers(True)
            
            self.output.set_auto_indent(True)
            self.output.set_insert_spaces_instead_of_tabs(True)
            self.output.set_tabs_width(4)

            self.output.set_show_margin(True)
            self.output.set_margin(80)

            self.output.modify_font(pango.FontDescription('monospace 9'))
            self.output.set_wrap_mode(gtk.WRAP_WORD)

            buffer = self.output.get_buffer()
            buffer.set_language(
                gtksourceview.SourceLanguagesManager()
                    .get_language_from_mime_type('text/x-python')
                    )
            
            buffer.set_check_brackets(True)
            buffer.set_highlight(True)
            
            buffer.connect('modified-changed', self.win.title)
    else:
        def edit_widget(self):
            self.output = gtk.TextView()
            
            self.output.modify_font(pango.FontDescription('monospace 9'))
            self.output.set_wrap_mode(gtk.WRAP_WORD)
            
            buffer = self.output.get_buffer()
            buffer.connect('modified-changed', self.win.title)

    def __init__(self, window):
        gtk.VBox.__init__(self)
        
        self.win = window
        
        self.edit_widget()

        topbox = gtk.ScrolledWindow()
        topbox.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        topbox.add(self.output)
        
        self.pack_end(topbox)

        self.show_all()
        
def get_menu_for(w):
    return (
        ('ScriptMenu', None, '_Script'),
            ('Save', gtk.STOCK_SAVE, '_Save', '<Control>S', None, w.save),
        )

menu_ui = """
<ui>
 <menubar name="MenuBar">
  <menu action="ScriptMenu">
   <menuitem action="Save"/>
  </menu>
 </menubar>
</ui>
"""

class EditorWindow(gtk.Window):
    def title(self, *args):
        if self.editor.output.get_buffer().get_modified():
            modified = '*'
        else:
            modified = ''
    
        self.set_title(
            "%s%s (%s)" % (
                modified,
                events.get_scriptname(self.filename),
                self.filename
                ))
                
    def load(self):
        text = file(self.filename).read()

        self.editor.load(text)
                
    def save(self, _action):
        if self.filename:
            text = self.editor.save()  
            
            file(self.filename, "wb").write(text)          
            
            if events.is_loaded(self.filename):            
                try:
                    events.reload(self.filename)
                    self.status.push(0, "Saved and reloaded %s" % self.filename)

                except ImportError, e:
                    self.status.push(0, "ImportError: %s" % e.msg)

                except SyntaxError, e:
                    self.status.push(0, "SyntaxError: %s" % e.msg)
                    self.editor.goto(e.lineno, e.offset)
            
            else:
                self.status.push(0, "Saved %s" % self.filename)

    def menu(self):
        actiongroup = gtk.ActionGroup('Edit')
        actiongroup.add_actions(get_menu_for(self))

        uimanager = gtk.UIManager()
        uimanager.add_ui_from_string(menu_ui)
        uimanager.insert_action_group(actiongroup, 0)
    
        accelgroup = uimanager.get_accel_group()
        self.add_accel_group(accelgroup)
        for action in actiongroup.list_actions():
            action.set_accel_group(accelgroup)
        
        actiongroup.get_action('Save').create_menu_item()
        
        return uimanager.get_widget("/MenuBar")

    def __init__(self, filename=''):
        gtk.Window.__init__(self)
        
        self.filename = filename
        
        try:
            self.set_icon(
                gtk.gdk.pixbuf_new_from_file(urk.path("urk_icon.svg"))
                )
        except:
            pass
            
        self.set_default_size(640, 480)

        self.editor = EditorWidget(self)

        if self.filename:
            self.load()
            self.title()

        self.status = gtk.Statusbar()
        self.status.set_has_resize_grip(True)
        
        menu = self.menu()

        box = gtk.VBox()
        box.pack_start(menu, expand=False)
        box.pack_start(self.editor)
        box.pack_end(self.status, expand=False)
        
        self.add(box)    
        self.show_all()

def main(filename=None):
    EditorWindow(filename)
