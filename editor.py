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
            
            buffer.connect('modified-changed', self.update_title)
    else:
        def edit_widget(self):
            self.output = gtk.TextView()
            
            self.output.modify_font(pango.FontDescription('monospace 9'))
            self.output.set_wrap_mode(gtk.WRAP_WORD)
            
            buffer.connect('modified-changed', self.update_title)

    def save(self, *args):
        if self.filename:
            buffer = self.output.get_buffer()
            text = buffer.get_text(
                buffer.get_start_iter(),
                buffer.get_end_iter()
                )

            file(self.filename, "wb").write(text)
            
            self.output.get_buffer().set_modified(False)
            
            if events.is_loaded(self.filename):            
                try:
                    events.reload(self.filename)
                    self.win.status.push(0, "Saved and reloaded %s" % self.filename)

                except ImportError, e:
                    self.win.status.push(0, "ImportError: %s" % e.msg)

                except SyntaxError, e:
                    buffer = self.output.get_buffer()
                    
                    cursor = buffer.get_iter_at_line_offset(
                        e.lineno-1, e.offset
                        )
                    
                    buffer.place_cursor(cursor)
                    self.output.scroll_to_iter(cursor, 0)
                
                    self.win.status.push(0, "SyntaxError: %s" % e.msg)
            
            else:
                self.win.status.push(0, "Saved %s" % self.filename)
    
    def update_title(self, *args):
        self.win.set_title(
            "%s%s (%s)" % (self.output.get_buffer().get_modified() and '*' or '', events.get_scriptname(self.filename), self.filename)
            )
    
    def __init__(self, window):
        gtk.VBox.__init__(self)
        
        self.win = window
        
        self.edit_widget()
        
        topbox = gtk.ScrolledWindow()
        topbox.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        topbox.add(self.output)
        
        self.pack_end(topbox)

        self.show_all()
        
def get_menu_for(editor):
    return (
        ('ScriptMenu', None, '_Script'),
            ('Save', gtk.STOCK_SAVE, '_Save', '<Control>S', None, editor.save),
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
    def __init__(self):
        gtk.Window.__init__(self)
        
        self.set_title('Edit-o-rama') # XXX replace this
        
        try:
            self.set_icon(
                gtk.gdk.pixbuf_new_from_file(urk.path("urk_icon.svg"))
                )
        except:
            pass
            
        self.set_default_size(640, 480)
        #self.set_border_width(5)

        self.editor = EditorWidget(self)
        self.status = gtk.Statusbar()
        self.status.set_has_resize_grip(True)

        actiongroup = gtk.ActionGroup('Edit')
        actiongroup.add_actions(get_menu_for(self.editor))

        uimanager = gtk.UIManager()
        uimanager.add_ui_from_string(menu_ui)
        uimanager.insert_action_group(actiongroup, 0)
    
        accelgroup = uimanager.get_accel_group()
        self.add_accel_group(accelgroup)
        for action in actiongroup.list_actions():
            action.set_accel_group(accelgroup)
        
        actiongroup.get_action('Save').create_menu_item()

        box = gtk.VBox()
        box.pack_start(uimanager.get_widget("/MenuBar"), expand=False)
        box.pack_start(self.editor)
        box.pack_end(self.status, expand=False)
        
        self.add(box)    
        self.show_all()

def edit(filename):
    widget = EditorWindow().editor
    
    if GTK_SOURCE_VIEW:
        widget.output.get_buffer().begin_not_undoable_action()

    widget.filename = filename
    widget.output.get_buffer().set_text(file(filename).read())
    widget.output.get_buffer().set_modified(False)
    widget.update_title()

    if GTK_SOURCE_VIEW:
        widget.output.get_buffer().end_not_undoable_action()

def main():
    EditorWindow()
