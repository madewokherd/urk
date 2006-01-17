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


class ScriptEditorWidget(gtk.VBox):
    if GTK_SOURCE_VIEW:
        def edit_widget(self):
            self.output = gtksourceview.SourceView(gtksourceview.SourceBuffer())
            
            self.output.set_auto_indent(True)
            self.output.set_show_line_numbers(True)
            self.output.set_insert_spaces_instead_of_tabs(True)
            self.output.set_show_margin(True)
            self.output.set_margin(80)
            self.output.modify_font(pango.FontDescription('monospace 9'))
            self.output.set_wrap_mode(gtk.WRAP_WORD)
            self.output.set_tabs_width(4)
            
            buffer = self.output.get_buffer()
            language = gtksourceview.SourceLanguagesManager(). \
                            get_language_from_mime_type('text/x-python')
            
            buffer.set_language(language)
            
            buffer.set_check_brackets(True)
            buffer.set_highlight(True)
    else:
        def edit_widget(self):
            self.output = gtk.TextView()
            
            self.output.modify_font(pango.FontDescription('monospace 9'))
            self.output.set_wrap_mode(gtk.WRAP_WORD)

    def save(self, button):
        if self.filename:
            buffer = self.output.get_buffer()
            text = buffer.get_text(
                buffer.get_start_iter(),
                buffer.get_end_iter()
                )

            file(self.filename, "wb").write(text)

            if events.is_loaded(self.filename):
                events.load(self.filename, True)
    
    def update_title(self):
        self.win.set_title("%s (%s)" % (events.get_modulename(self.filename),self.filename))
    
    def __init__(self):
        gtk.VBox.__init__(self)
        
        self.edit_widget()

        topbox = gtk.ScrolledWindow()
        topbox.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        topbox.add(self.output)

        self.pack_start(topbox)
        
        save_button = gtk.Button("Save")
        save_button.connect("clicked", self.save)
        self.pack_end(save_button, expand=False)

        self.show_all()

def edit(filename):
    widget = main()
    
    if GTK_SOURCE_VIEW:
        widget.output.get_buffer().begin_not_undoable_action()

    widget.output.get_buffer().set_text(file(filename).read())
    widget.filename = filename
    widget.update_title()

    if GTK_SOURCE_VIEW:
        widget.output.get_buffer().end_not_undoable_action()

def main():
    win = gtk.Window()
    win.set_title('Edit-o-rama') # XXX replace this
    
    try:
        w.set_icon(
            gtk.gdk.pixbuf_new_from_file(urk.path("urk_icon.svg"))
            )
    except:
        pass

    win.set_default_size(640, 480)
    win.set_border_width(5)
    
    widget = ScriptEditorWidget()
    widget.win = win    #This seems a bit wrong..
    
    win.add(widget)    
    win.show_all()
    
    return widget
