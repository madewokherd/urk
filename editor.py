import gc
import os
import sys
import traceback

import gtk
import pango

try:
    import gtksourceview
    GTK_SOURCE_VIEW = True
except:
    GTK_SOURCE_VIEW = False

import events
import urk

class EditorWidget(gtk.VBox):
    def goto(self, line, offset):
        buffer = self.output.get_buffer()
                    
        cursor = buffer.get_iter_at_line_offset(
            line-1, offset-1
            )
        
        buffer.place_cursor(cursor)
        self.output.scroll_to_iter(cursor, 0)

    def get_text(self):
        buffer = self.output.get_buffer()
        buffer.set_modified(False)
        
        return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter())
    
    def set_text(self, text):
        buffer = self.output.get_buffer()

        if GTK_SOURCE_VIEW:
            buffer.begin_not_undoable_action()

        buffer.set_text(text)
        buffer.set_modified(False)

        if GTK_SOURCE_VIEW:
            buffer.end_not_undoable_action()

    text = property(get_text, set_text)

    def edit_widget(self):
        if GTK_SOURCE_VIEW:
            self.output = gtksourceview.SourceView(gtksourceview.SourceBuffer())
        else:
            self.output = gtk.TextView()
            
        self.output.modify_font(pango.FontDescription('monospace 9'))
        self.output.set_wrap_mode(gtk.WRAP_WORD)
            
        if GTK_SOURCE_VIEW:
            self.output.set_show_line_numbers(True)
            self.output.set_show_line_markers(True)
            
            self.output.set_auto_indent(True)
            self.output.set_insert_spaces_instead_of_tabs(True)
            self.output.set_tabs_width(4)

            self.output.set_show_margin(True)
            self.output.set_margin(80)

            buffer = self.output.get_buffer()
            buffer.set_language(
                gtksourceview.SourceLanguagesManager()
                    .get_language_from_mime_type('text/x-python')
                    )
            
            buffer.set_check_brackets(True)
            buffer.set_highlight(True)

    def __init__(self):
        gtk.VBox.__init__(self)

        self.edit_widget()

        topbox = gtk.ScrolledWindow()
        topbox.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        topbox.add(self.output)
        
        self.pack_end(topbox)

        self.show_all()

menu_ui = """
<ui>
 <menubar name="MenuBar">
 
  <menu action="ScriptMenu">
   <menuitem action="Save"/>
   <menuitem action="Open"/>
  </menu>

 </menubar>
</ui>
"""

class ConfirmCloseDialog(gtk.Dialog):
    def __init__(self, parent, name):
        gtk.Dialog.__init__(self, "Question", parent,
                            gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT|gtk.DIALOG_NO_SEPARATOR,
                            ("Close without Saving", gtk.RESPONSE_CLOSE,
                            gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                            gtk.STOCK_SAVE, gtk.RESPONSE_OK,))
        self.set_property("resizable", False)
        self.set_property("border_width", 6)

        image = gtk.image_new_from_stock(gtk.STOCK_DIALOG_WARNING,gtk.ICON_SIZE_DIALOG)
        image.set_property("yalign",0.0)

        label = gtk.Label()
        label.set_property("selectable", True)
        label.set_markup(
"""<span weight="bold" size="larger">Save changes to script "%s" before closing?</span>

If you don't save, changes will be permanently lost.
""" % name)

        hbox = gtk.HBox(spacing=12)
        hbox.set_property('border-width', 6)
        hbox.pack_start(image)
        hbox.pack_end(label)
        
        self.vbox.set_property("spacing", 12)
        self.vbox.pack_start(hbox)

        self.show_all()

#This really is needed for pygtk 2.6
class ConfirmOverwriteDialog(gtk.Dialog):
    def __init__(self, parent, filename):
        gtk.Dialog.__init__(self, "Question", parent,
                            gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT|gtk.DIALOG_NO_SEPARATOR,
                            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                            "Replace", gtk.RESPONSE_OK,))
        self.set_property("resizable", False)
        self.set_property("border_width", 6)

        image = gtk.image_new_from_stock(gtk.STOCK_DIALOG_WARNING,gtk.ICON_SIZE_DIALOG)
        image.set_property("yalign",0.0)
        
        path, shortfile = os.path.split(filename)
        path = os.path.split(path)[1] or path

        label = gtk.Label()
        label.set_property("selectable", True)
        label.set_markup(
"""<span weight="bold" size="larger">A file named "%s" already exists.  Do you want to replace it?</span>
      
The file already exists in "%s".  Replacing it will overwrite its contents.
""" % (shortfile, path))

        hbox = gtk.HBox(spacing=12)
        hbox.set_property('border-width', 6)
        hbox.pack_start(image)
        hbox.pack_end(label)
        
        self.vbox.set_property("spacing", 12)
        self.vbox.pack_start(hbox)

        self.show_all()

class EditorWindow(gtk.Window):
    def title(self, *args):
        if self.editor.output.get_buffer().get_modified():
            modified = '*'
        else:
            modified = ''

        if self.filename:
            self.set_title(
                '%s%s (%s)' % (
                    modified,
                    events.get_scriptname(self.filename),
                    self.filename
                    ))
        else:
            self.set_title('%sNew Script' % modified)

    def open(self, _action):
        chooser = gtk.FileChooserDialog(
            "Open Script", self, gtk.FILE_CHOOSER_ACTION_OPEN,
            (
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OPEN, gtk.RESPONSE_OK
            )
            )

        chooser.set_current_folder(os.path.realpath(os.path.join(urk.userpath, 'scripts')))

        def on_response(dialog, response_id):
            if response_id == gtk.RESPONSE_OK:
                self.filename = chooser.get_filename()
                self.load()

            dialog.destroy()

        chooser.set_modal(True)
        chooser.show()
        chooser.connect("response", on_response)
    
    def load(self):
        if self.filename:
            self.editor.text = file(self.filename).read()
                
    def save(self, action=None, parent=None, on_save=lambda:None):
        if self.filename:
            file(self.filename, "wb").write(self.editor.text)          
            
            if events.is_loaded(self.filename):            
                try:
                    events.reload(self.filename)
                    self.status.push(0, "Saved and reloaded %s" % self.filename)

                except Exception, e:
                    if isinstance(e, SyntaxError) and self.filename == e.filename:
                        self.status.push(0, "SyntaxError: %s" % e.msg)
                        self.editor.goto(e.lineno, e.offset)
                    elif isinstance(e, SyntaxError):
                        self.status.push(0, "SyntaxError: %s (%s, line %s)" % (e.msg, e.filename, e.lineno))
                    else:
                        self.status.push(0, traceback.format_exception_only(sys.exc_type, sys.exc_value)[0].strip())
            
            else:
                self.status.push(0, "Saved %s" % self.filename)

            on_save()

        else:
            chooser = gtk.FileChooserDialog(
                "Save Script", parent or self, gtk.FILE_CHOOSER_ACTION_SAVE,
                (
                    gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                    gtk.STOCK_SAVE, gtk.RESPONSE_OK
                )
                )

            chooser.set_current_folder(os.path.realpath(os.path.join(urk.userpath, 'scripts')))
            chooser.set_default_response(gtk.RESPONSE_OK)

            def on_overwrite_response(confirm, response_id):
                confirm.destroy()
                if response_id == gtk.RESPONSE_OK:
                    self.filename = chooser.get_filename()
                    self.title()
                    self.save(action, parent, on_save)

                    chooser.destroy()

            def on_response(chooser, response_id):
                if response_id == gtk.RESPONSE_OK:
                    filename = chooser.get_filename()
                    if os.path.exists(filename):
                        confirm = ConfirmOverwriteDialog(chooser, filename)
                        confirm.connect("response", on_overwrite_response)

                    else:
                        self.filename = filename
                        self.title()
                        self.save(action)

                        chooser.destroy()

                else:
                    chooser.destroy()

            chooser.set_modal(True)
            chooser.connect("response", on_response)
            chooser.show()

    def menu(self):
        actions = (
            ('ScriptMenu', None, '_Script'),
                ('Save', gtk.STOCK_SAVE, '_Save', '<Control>S', None, self.save),
                ('Open', gtk.STOCK_OPEN, '_Open', '<Control>O', None, self.open),
            )
    
        actiongroup = gtk.ActionGroup('Edit')
        actiongroup.add_actions(actions)

        uimanager = gtk.UIManager()
        uimanager.add_ui_from_string(menu_ui)
        uimanager.insert_action_group(actiongroup, 0)
 
        self.add_accel_group(uimanager.get_accel_group())

        return uimanager.get_widget("/MenuBar")
    
    def on_delete(self, event):
        if self.editor.output.get_buffer().get_modified():
            dialog = ConfirmCloseDialog(self,
              self.filename and events.get_scriptname(self.filename) or "New Script")
            
            def on_response(widget, response_id):
                if response_id == gtk.RESPONSE_OK: #Save
                    def on_save():
                        widget.destroy()
                        self.destroy()
                    self.save(parent=widget, on_save=on_save)
                elif response_id == gtk.RESPONSE_CANCEL:
                    widget.destroy()
                elif response_id == gtk.RESPONSE_CLOSE:
                    widget.destroy()
                    self.destroy()
            
            dialog.connect("response", on_response)

            return True
    
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

        self.editor = EditorWidget()
        
        self.editor.output.get_buffer().connect('modified-changed', self.title)

        self.load()
        self.title()

        self.status = gtk.Statusbar()
        self.status.set_has_resize_grip(True)
        
        menu = self.menu()

        box = gtk.VBox()
        box.pack_start(menu, expand=False)
        box.pack_start(self.editor)
        box.pack_end(self.status, expand=False)
        
        self.connect("delete-event", EditorWindow.on_delete)
        
        try:
            self.set_icon(
                gtk.gdk.pixbuf_new_from_file(urk.path("urk_icon.svg"))
                )
        except:
            pass
        
        self.add(box)    
        self.show_all()

def main(filename=None):
    gc.collect()

    EditorWindow(filename)
