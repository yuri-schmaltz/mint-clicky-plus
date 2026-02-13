#!/usr/bin/python3
import gettext
import gi
import locale
import os
import setproctitle
import subprocess
import warnings
import sys
import traceback
import shortcuts
import datetime
from recorder import ScreenRecorder

# Suppress GTK deprecation warnings
warnings.filterwarnings("ignore")

gi.require_version("Gtk", "3.0")
gi.require_version('XApp', '1.0')
from gi.repository import Gtk, Gdk, Gio, XApp, GLib, GdkPixbuf

import utils
from common import *

class StopWindow(Gtk.Window):
    def __init__(self, callback):
        super().__init__(title="Clicky Stop")
        self.set_keep_above(True)
        self.set_decorated(False)
        self.set_resizable(False)
        self.callback = callback
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_spacing(5)
        # Style
        # context = box.get_style_context()
        # context.add_class("background")
        
        btn = Gtk.Button(label=_("Stop Recording"))
        # btn.get_style_context().add_class("destructive-action")
        btn.connect("clicked", self.on_stop)
        btn.set_size_request(120, 40)
        
        box.add(btn)
        self.add(box)
        self.show_all()
        
    def on_stop(self, widget):
        self.callback()
        self.destroy()

setproctitle.setproctitle("clickyplus")

# i18n
APP = 'clicky'

# Dynamic path resolution
script_dir = os.path.dirname(os.path.abspath(__file__))
# Check if running locally or installed
if os.path.exists(os.path.join(script_dir, "../../share/clicky")):
     # Local development structure (usr/lib/clicky -> usr/share/clicky)
     root_dir = os.path.abspath(os.path.join(script_dir, "../../.."))
     LOCALE_DIR = os.path.join(root_dir, "usr/share/locale")
     SHARE_DIR = os.path.join(root_dir, "usr/share/clicky")
else:
     # Installed system-wide
     LOCALE_DIR = "/usr/share/locale"
     SHARE_DIR = "/usr/share/clicky"

locale.bindtextdomain(APP, LOCALE_DIR)
gettext.bindtextdomain(APP, LOCALE_DIR)
gettext.textdomain(APP)
_ = gettext.gettext


class MyApplication(Gtk.Application):

    def __init__(self, application_id, flags):
        Gtk.Application.__init__(self, application_id=application_id, flags=flags)
        self.connect("activate", self.activate)
        
        # Add command line parsing
        self.add_main_option("area", ord('a'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE, "Capture area", None)
        self.add_main_option("screen", ord('s'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE, "Capture screen", None)
        self.add_main_option("window", ord('w'), GLib.OptionFlags.NONE, GLib.OptionArg.NONE, "Capture window", None)

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        self.cli_mode = None
        
        if options.contains("area"):
            self.cli_mode = "area"
        elif options.contains("screen"):
            self.cli_mode = "screen"
        elif options.contains("window"):
            self.cli_mode = "window"
            
        self.activate()
        return 0

    def activate(self, application=None):
        windows = self.get_windows()
        if (len(windows) > 0):
            window = windows[0]
            window.present()
            window.show()
        else:
            # Check if we have a CLI mode set
            cli_mode = getattr(self, 'cli_mode', None)
            
            window = MainWindow(self)
            self.add_window(window.window)
            
            if cli_mode:
                # Direct capture mode
                window.set_mode_and_capture(cli_mode)
            else:
                window.window.show()

class MainWindow():

    def __init__(self, application):

        self.application = application
        self.settings = Gio.Settings(schema_id="org.x.clickyplus")

        # Main UI
        gladefile = os.path.join(SHARE_DIR, "clicky.ui")
        self.builder = Gtk.Builder()
        self.builder.set_translation_domain(APP)
        self.builder.add_from_file(gladefile)
        self.window = self.builder.get_object("main_window")
        self.window.set_title(_("Clicky Plus"))
        self.window.set_icon_name("clicky")
        self.window.set_resizable(False)
        self.stack = self.builder.get_object("stack")
        self.stack.set_homogeneous(False)
        self.main_content_box = self.builder.get_object("main_content_box")
        self.screenshot_box = self.builder.get_object("screenshot_box")
        
        self.toggle_mode_screen = self.builder.get_object("toggle_mode_screen")
        self.toggle_mode_window = self.builder.get_object("toggle_mode_window")
        self.toggle_mode_area = self.builder.get_object("toggle_mode_area")
        
        self.radio_type_photo = self.builder.get_object("radio_type_photo")
        self.radio_type_video = self.builder.get_object("radio_type_video")
        
        self.chooser_folder = self.builder.get_object("chooser_folder")
        self.switch_clipboard = self.builder.get_object("switch_clipboard")
        self.combo_format = self.builder.get_object("combo_format")
        self.entry_filename = self.builder.get_object("entry_filename")

        self.switch_pointer = self.builder.get_object("switch_pointer")
        self.switch_sound = self.builder.get_object("switch_sound")
        self.spin_delay = self.builder.get_object("spin_delay")
        self.switch_set_default = self.builder.get_object("switch_set_default")

        # CSS
        provider = Gtk.CssProvider()
        provider.load_from_path(os.path.join(SHARE_DIR, "clicky.css"))
        screen = Gdk.Display.get_default_screen(Gdk.Display.get_default())
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Settings
        prefer_dark_mode = self.settings.get_boolean("prefer-dark-mode")
        Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", prefer_dark_mode)

        mode = self.settings.get_string("capture-mode")
        if mode == "screen": self.toggle_mode_screen.set_active(True)
        elif mode == "window": self.toggle_mode_window.set_active(True)
        elif mode == "area": self.toggle_mode_area.set_active(True)

        self.settings.bind("include-pointer", self.switch_pointer, "active", Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("enable-sound", self.switch_sound, "active", Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("delay", self.spin_delay, "value", Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("set-as-default", self.switch_set_default, "active", Gio.SettingsBindFlags.DEFAULT)
        self.switch_set_default.connect("notify::active", self.on_set_default_toggled)

        # Storage settings bindings
        self.settings.bind("auto-copy-clipboard", self.switch_clipboard, "active", Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("filename-pattern", self.entry_filename, "text", Gio.SettingsBindFlags.DEFAULT)
        # Manual sync for folder chooser (GSettings doesn't bind 'current-folder' property of FileChooserButton)
        save_dir = self.settings.get_string("save-directory")
        if save_dir and os.path.exists(save_dir):
            self.chooser_folder.set_current_folder(save_dir)
        self.chooser_folder.connect("current-folder-changed", self.on_folder_changed)
        # Using active-id for combo box
        self.settings.bind("file-format", self.combo_format, "active-id", Gio.SettingsBindFlags.DEFAULT)

        # import xapp.SettingsWidgets
        # spin = xapp.SettingsWidgets.SpinButton(_("Delay"), units="seconds")
        # self.builder.get_object("box_options").pack_start(spin, False, False, 0)
        
        self.recorder = ScreenRecorder()
        self.stop_window = None

        self.window.show()
        self.builder.get_object("button_take_screenshot").grab_focus()

        # Store initial window size to keep UI stable across captures
        self.fixed_size = None
        def store_initial_size():
            self.fixed_size = self.window.get_size()
            self.apply_fixed_layout()
            return False
        GLib.idle_add(store_initial_size)

        self.builder.get_object("go_back_button").hide()

        # Widget signals
        self.window.connect("key-press-event",self.on_key_press_event)
        self.window.connect("size-allocate", self.on_window_size_allocate)
        self.builder.get_object("go_back_button").connect("clicked", self.go_back)
        
        self.btn_capture = self.builder.get_object("button_take_screenshot")
        self.btn_capture.connect("clicked", self.on_capture_click)
        
        self.toggle_mode_screen.connect("toggled", self.on_capture_mode_toggled)
        self.toggle_mode_window.connect("toggled", self.on_capture_mode_toggled)
        self.toggle_mode_area.connect("toggled", self.on_capture_mode_toggled)
        
        self.radio_type_photo.connect("toggled", self.on_type_toggled)
        self.radio_type_video.connect("toggled", self.on_type_toggled)

        self.builder.get_object("button_help").connect("clicked", self.open_keyboard_shortcuts)
        self.builder.get_object("button_about").connect("clicked", self.open_about)

    def get_capture_mode(self):
        if self.toggle_mode_screen.get_active():
            mode = CAPTURE_MODE_SCREEN
        elif self.toggle_mode_window.get_active():
            mode = CAPTURE_MODE_WINDOW
        else:
            mode = CAPTURE_MODE_AREA
        return mode

    def on_set_default_toggled(self, switch, _pspec):
        """Called when the 'set as default' toggle changes."""
        if switch.get_active():
            shortcuts.enable()
        else:
            shortcuts.disable()

    def on_capture_mode_toggled(self, widget):
        self.settings.set_string("capture-mode", self.get_capture_mode())
        
    def on_folder_changed(self, widget):
        folder = widget.get_current_folder()
        if folder:
            self.settings.set_string("save-directory", folder)
        
    def on_type_toggled(self, widget):
        is_video = self.radio_type_video.get_active()
        if is_video:
             self.btn_capture.set_label(_("Record Video"))
             self.update_format_combo("video")
        else:
             self.btn_capture.set_label(_("Take Screenshot"))
             self.update_format_combo("photo")
             
    def update_format_combo(self, mode):
        # We need to block signals or rely on binding.
        # Since binding is active, changing active-id might update settings.
        # Better to just update list store if possible, but GtkComboBoxText doesn't expose store easily?
        # Actually it does `get_model()`.
        self.combo_format.remove_all()
        if mode == "video":
            self.combo_format.append("webm", "WebM")
            self.combo_format.append("gif", "GIF")
            self.combo_format.set_active_id("webm")
        else:
            self.combo_format.append("png", "PNG")
            self.combo_format.append("jpg", "JPG")
            self.combo_format.append("webp", "WebP")
            # Restore setting or default
            fmt = self.settings.get_string("file-format")
            if fmt not in ["png", "jpg", "webp"]: fmt = "png"
            self.combo_format.set_active_id(fmt)

    def on_capture_click(self, widget):
        if self.radio_type_video.get_active():
            self.start_video_recording()
        else:
            self.start_screenshot(widget)

    def start_screenshot(self, widget):
        self.hide_window()
        # Increased to 500ms to ensure compositor animations (fade-out) are complete
        delay_seconds = self.settings.get_int("delay")
        delay_ms = max(0, int(delay_seconds)) * 1000
        GLib.timeout_add(500 + delay_ms, self.take_screenshot)

    def hide_window(self):
        self.window.hide()
        self.window.set_opacity(0)
        self.window.set_skip_pager_hint(True)
        self.window.set_skip_taskbar_hint(True)

    def show_window(self):
        self.window.show()
        self.window.set_opacity(1)
        self.window.set_skip_pager_hint(False)
        self.window.set_skip_taskbar_hint(False)

    def show_error_dialog(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=_("Screenshot Failed"),
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def set_mode_and_capture(self, mode):
        # Map string mode to radio button or constant
        # Map string mode to radio button or constant
        if mode == "screen":
            self.toggle_mode_screen.set_active(True)
        elif mode == "window":
            self.toggle_mode_window.set_active(True)
        elif mode == "area":
            self.toggle_mode_area.set_active(True)
            
        # Start capture immediately
        self.start_screenshot(None)

    def set_canvas_mode(self, widget, mode):
        self.canvas.current_tool = mode

    def setup_canvas_ui(self):
        if hasattr(self, 'canvas_toolbar'):
            return

        # Get the container box
        box = self.builder.get_object("screenshot_box")
        
        # Main vertical container for toolbar rows
        vbox_toolbar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox_toolbar.set_margin_start(4)
        vbox_toolbar.set_margin_end(4)
        
        # Row 1: Tools
        toolbar1 = Gtk.Toolbar()
        toolbar1.set_style(Gtk.ToolbarStyle.ICONS)
        toolbar1.set_icon_size(Gtk.IconSize.LARGE_TOOLBAR)
        
        def add_tool(icon, tooltip, tool_mode):
            btn = Gtk.ToolButton()
            btn.set_icon_name(icon)
            btn.set_tooltip_text(tooltip)
            btn.connect("clicked", self.set_canvas_mode, tool_mode)
            toolbar1.insert(btn, -1)
            return btn

        add_tool("draw-freehand-symbolic", _("Pen"), "pen")
        add_tool("marker-symbolic", _("Highlighter"), "highlighter")
        toolbar1.insert(Gtk.SeparatorToolItem(), -1)
        add_tool("draw-rectangle-symbolic", _("Rectangle"), "rectangle")
        add_tool("draw-ellipse-symbolic", _("Circle"), "circle")
        add_tool("draw-line-symbolic", _("Line"), "line")
        add_tool("go-next-symbolic", _("Arrow"), "arrow")
        add_tool("format-text-bold-symbolic", _("Text"), "text")
        add_tool("weather-fog-symbolic", _("Blur"), "blur")
        toolbar1.insert(Gtk.SeparatorToolItem(), -1)
        add_tool("edit-cut-symbolic", _("Crop Image"), "crop")
        add_tool("edit-clear-symbolic", _("Eraser"), "eraser")
        
        toolbar1.insert(Gtk.SeparatorToolItem(), -1)
        btn_save = Gtk.ToolButton()
        btn_save.set_icon_name("document-save-symbolic")
        btn_save.set_tooltip_text(_("Save"))
        btn_save.connect("clicked", self.save_canvas)
        toolbar1.insert(btn_save, -1)

        vbox_toolbar.pack_start(toolbar1, False, False, 0)

        # Row 2: Properties
        prop_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        prop_row.set_margin_top(2)
        prop_row.set_margin_bottom(6)
        prop_row.set_halign(Gtk.Align.CENTER)
        
        # Color
        color_btn = Gtk.ColorButton.new_with_rgba(Gdk.RGBA(1, 0, 0, 1))
        color_btn.connect("color-set", lambda b: self.canvas.set_stroke_color(b.get_rgba()))
        prop_row.pack_start(color_btn, False, False, 0)
        
        # Line Width
        adj = Gtk.Adjustment(3, 1, 50, 1, 5, 0)
        width_spin = Gtk.SpinButton.new(adj, 1, 0)
        width_spin.connect("value-changed", lambda s: self.canvas.set_line_width(s.get_value()))
        prop_row.pack_start(width_spin, False, False, 0)
        
        # Fill
        fill_check = Gtk.CheckButton.new_with_label(_("Fill"))
        fill_check.connect("toggled", lambda c: self.canvas.set_fill_active(c.get_active()))
        prop_row.pack_start(fill_check, False, False, 0)
        
        # Opacity
        prop_row.pack_start(Gtk.Label(label=_("Opacity:")), False, False, 0)
        opacity_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.1, 1.0, 0.1)
        opacity_scale.set_value(1.0)
        opacity_scale.set_size_request(100, -1)
        opacity_scale.connect("value-changed", lambda s: self.canvas.set_opacity(s.get_value()))
        prop_row.pack_start(opacity_scale, False, False, 0)

        vbox_toolbar.pack_start(prop_row, False, False, 0)
        vbox_toolbar.show_all()
        self.canvas_toolbar = vbox_toolbar
        
        box.pack_start(vbox_toolbar, False, False, 0)
        box.reorder_child(vbox_toolbar, 0)
        
        # Replace Image with Canvas
        self.old_image_widget = self.builder.get_object("screenshot_image")
        self.old_image_widget.hide()
        
        from canvas import CanvasWidget
        self.canvas = CanvasWidget()
        self.canvas.show()

        # Center the canvas inside the container
        # Center the canvas inside the container
        # Use Overlay to support floating widgets (Text Entry)
        self.preview_container = Gtk.Overlay()
        self.preview_container.set_valign(Gtk.Align.CENTER)
        self.preview_container.set_halign(Gtk.Align.CENTER)
        self.preview_container.add(self.canvas)
        
        # Hidden text entry for text tool
        self.text_entry = Gtk.Entry()
        self.text_entry.set_visible(False)
        self.text_entry.set_width_chars(20)
        # We don't fix position yet, the canvas will move it
        self.preview_container.add_overlay(self.text_entry)
        
        self.canvas.set_text_entry(self.text_entry, self.preview_container)
        
        self.preview_container.show_all()
        # Hide entry again as show_all shows it
        self.text_entry.hide()

        box.pack_start(self.preview_container, True, True, 0)

        if self.fixed_size:
            self.apply_fixed_layout()

        if self.fixed_size:
            self.apply_fixed_layout()
            
    def start_video_recording(self):
        self.hide_window()
        
        # Determine Area
        mode = self.get_capture_mode()
        rect = None
        
        if mode == CAPTURE_MODE_AREA:
             # Delay slightly to allow hide?
             GLib.usleep(200000) # 0.2s
             rect = utils.select_area_interactive()
             if not rect:
                 self.show_window()
                 return
             x, y, w, h = rect.x, rect.y, rect.width, rect.height
        elif mode == CAPTURE_MODE_WINDOW:
             # Window selection for video is tricky (window moves).
             # Usually we grab window geometry once and fixed area.
             # Reusing x11 capture logic for finding window?
             # For now, let's treat Window same as Area (interactive selection) or use utils helper?
             # utils.capture_via_x11 gets window geometry.
             # We can't easily select window interactively without taking a screenshot first?
             # utils.find_current_window() works based on active window *after* delay.
             
             # Fallback to Area selection for Window mode in Video (common pattern)
             # Or auto-detect active window after delay?
             
             # Let's prompt for area for now to be safe/clear.
             GLib.usleep(200000)
             rect = utils.select_area_interactive()
             if not rect:
                 self.show_window()
                 return
             x, y, w, h = rect.x, rect.y, rect.width, rect.height
        else:
             # Full Screen
             screen = Gdk.Screen.get_default()
             x, y = 0, 0
             w = screen.get_width()
             h = screen.get_height()
        
        # Output File
        save_dir = self.settings.get_string("save-directory")
        if not save_dir:
            save_dir = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES)
            if not save_dir: save_dir = os.path.expanduser("~")
            
        fmt = self.combo_format.get_active_id() # Use combo value (video formats)
        if not fmt: fmt = "webm"
        
        pattern = self.settings.get_string("filename-pattern")
        try:
             filename = datetime.datetime.now().strftime(pattern)
        except:
             filename = "Screencast"
             
        if not filename.lower().endswith("." + fmt):
            filename += "." + fmt
            
        output_path = os.path.join(save_dir, filename)
        
        if self.recorder.start(x, y, w, h, output_path, fmt):
             self.stop_window = StopWindow(self.stop_recording)
             # Position stop window bottom right
             stop_w, stop_h = 150, 60
             screen_w = Gdk.Screen.get_default().get_width()
             screen_h = Gdk.Screen.get_default().get_height()
             self.stop_window.move(screen_w - stop_w - 20, screen_h - stop_h - 50)
        else:
             self.show_window()
             self.show_error_dialog(_("Failed to start recording"))

    def stop_recording(self):
        saved_path = self.recorder.stop()
        self.stop_window = None
        self.show_window()
        
        if saved_path:
             notification = Gio.Notification.new(_("SCREENCAST SAVED"))
             notification.set_body(saved_path)
             notification.set_icon(Gio.ThemedIcon.new("video-x-generic"))
             if self.application:
                 self.application.send_notification("clicky-video", notification)

    def save_canvas(self, widget):
        if not self.canvas: return
        
        pixbuf = self.canvas.get_result_pixbuf()
        if not pixbuf: return

        # Settings
        save_dir = self.settings.get_string("save-directory")
        if not save_dir:
            save_dir = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES)
            if not save_dir: 
                save_dir = os.path.expanduser("~")
        
        fmt = self.settings.get_string("file-format")
        ptrn = self.settings.get_string("filename-pattern")

        try:
            filename = datetime.datetime.now().strftime(ptrn)
        except:
             filename = "Screenshot-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        
        if not filename.lower().endswith("." + fmt):
            filename += "." + fmt
            
        full_path = os.path.join(save_dir, filename)
        
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir)
            except:
                self.show_error_dialog(_("Could not create directory") + ": " + save_dir)
                return
        
        try:
            if fmt == "jpg":
                pixbuf.savev(full_path, "jpeg", ["quality"], ["90"])
            elif fmt == "webp":
                 try:
                     pixbuf.savev(full_path, "webp", [], [])
                 except: # Fallback
                     full_path = full_path.rsplit('.', 1)[0] + ".png"
                     pixbuf.savev(full_path, "png", [], [])
            else:
                pixbuf.savev(full_path, "png", [], [])

            notification = Gio.Notification.new(_("Screenshot Saved"))
            notification.set_body(full_path)
            notification.set_icon(Gio.ThemedIcon.new("image-x-generic"))
            
            if self.application:
                self.application.send_notification("clicky-saved", notification)
            
            # Show saved state in UI or trigger open folder
            # For now, just a visual cue could be helpful, but notification handles it.
            
        except Exception as e:
            self.show_error_dialog(str(e))


    def go_back(self, widget):
        self.navigate_to("main_page")
        if self.fixed_size:
            self.apply_fixed_layout()
            self.window.resize(self.fixed_size[0], self.fixed_size[1])

    def copy_to_clipboard(self, pixbuf):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_image(pixbuf)
        clipboard.store()

    def show_notification(self):
        notification = Gio.Notification.new(_("Screenshot Taken"))
        if self.settings.get_boolean("auto-copy-clipboard"):
            notification.set_body(_("Image copied to clipboard."))
        else:
            notification.set_body(_("Click to edit and save."))
        notification.set_icon(Gio.ThemedIcon.new("clicky"))
        
        if self.application:
            self.application.send_notification("screenshot-taken", notification)

    def apply_fixed_layout(self, width=None, height=None):
        if width is None or height is None:
            # Reverting to Main Page (Compact Menu)
            if not self.fixed_size:
                return
            width, height = self.fixed_size
            is_main = True
        else:
            is_main = False
        
        # CRITICAL: Reset ALL constraints before applying new ones
        self.window.set_geometry_hints(None, None, 0)
        self.window.set_resizable(True)

        if is_main:
            # Force small main menu size
            self.stack.set_size_request(-1, -1)
            self.main_content_box.set_size_request(-1, -1)
            if hasattr(self, 'preview_container'):
                self.preview_container.set_size_request(-1, -1)

            # Strict hints for main menu
            geometry = Gdk.Geometry()
            geometry.min_width = width
            geometry.max_width = width
            geometry.min_height = height
            geometry.max_height = height
            self.window.set_geometry_hints(None, geometry, Gdk.WindowHints.MIN_SIZE | Gdk.WindowHints.MAX_SIZE)
            self.window.resize(width, height)
            self.window.set_resizable(False)
            return

        # Screenshot Preview Logic
        self.current_fixed_size = (width, height)
        
        if hasattr(self, 'preview_container'):
             self.preview_container.set_size_request(width, height)
            
        if hasattr(self, 'canvas'):
            self.canvas.set_size_request(width, height)

        ui_height_offset = 150 # Buffer for Header + Two-row toolbar
        
        geometry = Gdk.Geometry()
        geometry.min_width = width
        geometry.max_width = width
        geometry.min_height = height + ui_height_offset
        geometry.max_height = height + ui_height_offset
        
        self.window.set_geometry_hints(None, geometry, Gdk.WindowHints.MIN_SIZE | Gdk.WindowHints.MAX_SIZE)
        self.window.resize(width, height + ui_height_offset)
        self.window.set_resizable(False)

    def on_window_size_allocate(self, widget, allocation):
        if self.fixed_size is None:
            self.fixed_size = (allocation.width, allocation.height)
            self.apply_fixed_layout()
            return
    def take_screenshot(self):
        try:
            options = Options(self.settings)
            pixbuf = utils.capture_pixbuf(options)
            
            # Post-capture actions
            if pixbuf:
                if self.settings.get_boolean("auto-copy-clipboard"):
                    self.copy_to_clipboard(pixbuf)
                self.show_notification()
                
                # Setup Canvas Logic
                if not hasattr(self, 'canvas'):
                    self.setup_canvas_ui()
                
                # Scaling Threshold (1280px)
                display_pixbuf = pixbuf
                if pixbuf.get_width() >= 1920:
                    # Strictly 50% for 1080p and above
                    target_w = pixbuf.get_width() // 2
                    target_h = pixbuf.get_height() // 2
                    display_pixbuf = pixbuf.scale_simple(target_w, target_h, GdkPixbuf.InterpType.BILINEAR)
                elif pixbuf.get_width() > 1280:
                    # Proportional scaling for intermediate sizes
                    target_w = pixbuf.get_width() // 2
                    target_h = pixbuf.get_height() // 2
                    display_pixbuf = pixbuf.scale_simple(target_w, target_h, GdkPixbuf.InterpType.BILINEAR)
                
                self.canvas.set_pixbuf(display_pixbuf)
                
                # Set window size to match preview (with some buffer)
                target_w = display_pixbuf.get_width()
                target_h = display_pixbuf.get_height()
                
                self.apply_fixed_layout(target_w, target_h)
                
                self.navigate_to("screenshot_page")
                self.show_window()
            else:
                self.show_error_dialog(_("Screenshot canceled or failed."))
                self.navigate_to("main_page")
                self.show_window()
        except Exception as e:
            print(traceback.format_exc())
            self.show_error_dialog(_("An error occurred during the screenshot:\n\n") + str(e))
            self.show_window()

    @idle_function
    def navigate_to(self, page, name=""):
        if page == "main_page":
            self.builder.get_object("go_back_button").hide()
        else:
            self.builder.get_object("go_back_button").show()
        self.stack.set_visible_child_name(page)

    def open_about(self, widget):
        dlg = Gtk.AboutDialog()
        dlg.set_transient_for(self.window)
        dlg.set_title(_("About"))
        dlg.set_program_name(_("Clicky Plus"))
        dlg.set_comments(_("Save images of your screen or individual windows"))
        try:
            h = open('/usr/share/common-licenses/GPL', encoding="utf-8")
            s = h.readlines()
            gpl = ""
            for line in s:
                gpl += line
            h.close()
            dlg.set_license(gpl)
        except Exception as e:
            print (e)

        dlg.set_version("1.1.0")
        dlg.set_icon_name("clicky")
        dlg.set_logo_icon_name("clicky")
        dlg.set_website("https://github.com/yuri-schmaltz/mint-clicky")
        def close(w, res):
            if res == Gtk.ResponseType.CANCEL or res == Gtk.ResponseType.DELETE_EVENT:
                w.destroy()
        dlg.connect("response", close)
        dlg.show()

    def open_keyboard_shortcuts(self, widget):
        gladefile = os.path.join(SHARE_DIR, "shortcuts.ui")
        builder = Gtk.Builder()
        builder.set_translation_domain(APP)
        builder.add_from_file(gladefile)
        window = builder.get_object("shortcuts")
        window.set_title(_("Screenshot"))
        window.show()

    def on_menu_quit(self, widget):
        self.application.quit()

    def on_key_press_event(self, widget, event):
        persistant_modifiers = Gtk.accelerator_get_default_mod_mask()
        modifier = event.get_state() & persistant_modifiers
        ctrl = modifier == Gdk.ModifierType.CONTROL_MASK
        shift = modifier == Gdk.ModifierType.SHIFT_MASK

        if ctrl and event.keyval == Gdk.KEY_r:
            # Ctrl + R
            pass
        elif ctrl and event.keyval == Gdk.KEY_f:
            # Ctrl + F
            pass
        elif event.keyval == Gdk.KEY_F11:
             # F11..
             pass
        elif self.stack.get_visible_child_name() == "screenshot_page":
            alt = modifier == Gdk.ModifierType.MOD1_MASK
            if event.keyval == Gdk.KEY_BackSpace:
                self.navigate_to("main_page")
            elif alt and event.keyval == Gdk.KEY_Left:
                self.navigate_to("main_page")

if __name__ == "__main__":
    application = MyApplication("org.x.clicky", Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
    application.run(sys.argv)

