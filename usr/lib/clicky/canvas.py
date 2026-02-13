import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf
import cairo
import math
from gi.repository import Pango, PangoCairo
from PIL import Image, ImageFilter
import sys
import ctypes

class CanvasWidget(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_button_press)
        self.connect("motion-notify-event", self.on_motion_notify)
        self.connect("button-release-event", self.on_button_release)
        self.connect("size-allocate", self.on_size_allocate)

        self.surface = None
        self.image_surface = None
        self.original_pixbuf = None
        
        # Tools: 'pen', 'highlighter', 'rectangle', 'circle', 'line', 'arrow', 'crop'
        self.current_tool = 'pen' 
        self.is_drawing = False
        self.start_x = 0
        self.start_y = 0
        self.last_x = 0
        self.last_y = 0

        # Styles
        self.stroke_color = Gdk.RGBA(1, 0, 0, 1) # Default Red
        self.line_width = 3
        self.fill_active = False
        self.opacity = 1.0

    def set_stroke_color(self, rgba):
        self.stroke_color = rgba
        
    def set_line_width(self, width):
        self.line_width = width
        
    def set_fill_active(self, active):
        self.fill_active = active
        
    def set_opacity(self, opacity):
        self.opacity = opacity

    def set_text_entry(self, entry, overlay):
        self.text_entry = entry
        self.overlay = overlay
        self.text_entry.connect("activate", self.on_text_commit)
        self.text_entry.connect("focus-out-event", self.on_text_focus_out)
        
    def on_text_commit(self, entry):
        text = entry.get_text()
        if text:
            self.commit_text(text)
        entry.hide()
        self.text_entry.set_text("")
        # Return focus to canvas?
        # self.grab_focus()

    def on_text_focus_out(self, entry, event):
        self.on_text_commit(entry)
        return False
        
    def commit_text(self, text):
        cr = cairo.Context(self.surface)
        self.apply_style(cr)
        
        # Adjust position to baseline (approx)
        # Entry widget has height, text baseline is usually middle-ish.
        # Let's verify start_x, start_y
        
        layout = PangoCairo.create_layout(cr)
        layout.set_text(text, -1)
        
        desc = Pango.FontDescription("Sans Bold 20")
        desc.set_size(int(self.line_width * 10 * Pango.SCALE)) # Scale font with line width?
        # Or fixed size? Or separate font size control?
        # For now, let's use line_width as a proxy or fixed.
        # let's use a reasonable size.
        desc.set_absolute_size(20 * Pango.SCALE + self.line_width * Pango.SCALE)
        layout.set_font_description(desc)
        
        cr.move_to(self.start_x, self.start_y)
        PangoCairo.show_layout(cr, layout)
        
        self.queue_draw()

    def set_pixbuf(self, pixbuf):
        self.original_pixbuf = pixbuf
        if pixbuf is None:
            return

        width = pixbuf.get_width()
        height = pixbuf.get_height()
        self.set_size_request(width, height)

        if self.surface is None or self.surface.get_width() != width or self.surface.get_height() != height:
            self.create_surface(width, height)

        self.redraw_canvas()
        self.queue_draw()

    def on_size_allocate(self, widget, allocation):
        # When resized, we might arguably want to keep the surface or resize it.
        # For simplicity in a screenshot tool, the canvas size usually matches image size
        # or we accept the allocation.
        # Let's create a surface that matches the allocation if it doesn't exist
        if self.surface is None or self.surface.get_width() != allocation.width or self.surface.get_height() != allocation.height:
             self.create_surface(allocation.width, allocation.height)
             self.redraw_canvas()

    def create_surface(self, width, height):
        window = self.get_window()
        if window is not None:
            self.surface = window.create_similar_surface(
                cairo.CONTENT_COLOR_ALPHA, width, height)
        else:
            self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        
        # Clear surface
        cr = cairo.Context(self.surface)
        cr.set_source_rgba(0.2, 0.2, 0.2, 1) # Dark gray background
        cr.paint()

    def redraw_canvas(self):
        if self.surface is None: 
            return
            
        cr = cairo.Context(self.surface)
        
        # 1. Clear text/drawings
        cr.set_source_rgba(0.2, 0.2, 0.2, 1)
        cr.paint()
        
        # 2. Draw Image
        if self.original_pixbuf:
            Gdk.cairo_set_source_pixbuf(cr, self.original_pixbuf, 0, 0)
            cr.paint()
            
        # If we had a history of paths, we would redraw them here.
        # For this simple "paint on surface" implementation, we just clear and paste image.
        # A more complex one would keep strokes in a list. 
        # For MVP: drawings are destructive on the surface? 
        # No, let's keep a separate "drawing layer" if possible, or just paint fast.
        # Decision: "Paint on top" architecture. Resetting pixbuf clears drawings.
        pass

    def on_draw(self, widget, cr):
        # 1. Draw the permanent surface (Image + Committed Drawings)
        if self.surface:
            cr.set_source_surface(self.surface, 0, 0)
            cr.paint()
            
        # 2. Draw the transient overlay (Shape being dragged / Crop selection)
        if self.is_drawing and self.current_tool in ['rectangle', 'circle', 'line', 'arrow', 'crop']:
            self.draw_overlay(cr)
            
        return False

    def on_button_press(self, widget, event):
        if event.button == 1 and self.surface:
            self.is_drawing = True
            
            # Start point
            self.start_x = event.x
            self.start_y = event.y
            self.last_x = event.x
            self.last_y = event.y
            
            # For Pen/Highlighter, we start drawing immediately
            if self.current_tool in ['pen', 'highlighter', 'eraser']:
                pass # Handled in motion
            elif self.current_tool == 'text':
                self.text_entry.set_halign(Gtk.Align.START)
                self.text_entry.set_valign(Gtk.Align.START)
                self.text_entry.set_margin_start(int(event.x))
                self.text_entry.set_margin_top(int(event.y))
                self.text_entry.set_visible(True)
                self.text_entry.grab_focus()
                
        return True
                
        return True

    def on_motion_notify(self, widget, event):
        self.last_x = event.x
        self.last_y = event.y

        if self.is_drawing:
            if self.current_tool in ['pen', 'highlighter', 'eraser'] and self.surface:
                self.draw_stroke(event.x, event.y)
                # Update start for next segment
                self.start_x = event.x
                self.start_y = event.y
            elif self.current_tool in ['rectangle', 'circle', 'line', 'arrow', 'crop']:
                # Queue draw to update overlay
                self.queue_draw()
                
        return True

    def on_button_release(self, widget, event):
        if event.button == 1 and self.is_drawing:
            self.is_drawing = False
            
            if self.current_tool in ['rectangle', 'circle', 'line', 'arrow']:
                self.commit_shape(event.x, event.y)
            elif self.current_tool == 'crop':
                self.apply_crop(event.x, event.y)
            elif self.current_tool == 'blur':
                self.apply_blur(event.x, event.y)
            elif self.current_tool in ['pen', 'highlighter', 'eraser']:
                self.draw_stroke(event.x, event.y) # Final segment
        return True

    def apply_style(self, cr):
        color = self.stroke_color
        cr.set_source_rgba(color.red, color.green, color.blue, color.alpha * self.opacity)
        cr.set_line_width(self.line_width)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

    def draw_arrow(self, cr, x1, y1, x2, y2):
        cr.move_to(x1, y1)
        cr.line_to(x2, y2)
        cr.stroke()
        
        # Arrow head
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_len = 10 + self.line_width * 2
        arrow_angle = math.pi / 6
        
        cr.move_to(x2, y2)
        cr.line_to(x2 - arrow_len * math.cos(angle - arrow_angle),
                   y2 - arrow_len * math.sin(angle - arrow_angle))
        cr.move_to(x2, y2)
        cr.line_to(x2 - arrow_len * math.cos(angle + arrow_angle),
                   y2 - arrow_len * math.sin(angle + arrow_angle))
        cr.stroke()

    def draw_overlay(self, cr):
        # Draw the shape currently being defined by start_x,y -> last_x,y
        x = min(self.start_x, self.last_x)
        y = min(self.start_y, self.last_y)
        w = abs(self.start_x - self.last_x)
        h = abs(self.start_y - self.last_y)
        
        if self.current_tool == 'crop':
            # Dim everything
            cr.set_source_rgba(0, 0, 0, 0.5)
            cr.paint()
            
            # Clear the selection
            cr.set_operator(cairo.OPERATOR_SOURCE)
            cr.set_source_rgba(0, 0, 0, 0) # Transparent
            cr.rectangle(x, y, w, h)
            cr.fill()
            
            # Restore operator
            cr.set_operator(cairo.OPERATOR_OVER)
            
            # White Border
            cr.set_source_rgba(1, 1, 1, 1)
            cr.set_line_width(1)
            cr.set_dash([4.0, 4.0], 0)
            cr.rectangle(x, y, w, h)
            cr.stroke()
            cr.stroke()
            return
            
        if self.current_tool == 'blur':
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.3)
            cr.rectangle(x, y, w, h)
            cr.fill()
            cr.set_source_rgba(1, 1, 1, 0.5)
            cr.set_line_width(1)
            cr.rectangle(x, y, w, h)
            cr.stroke()
            return

        self.apply_style(cr)
            
        if self.current_tool == 'rectangle':
            cr.rectangle(x, y, w, h)
            if self.fill_active:
                cr.fill_preserve()
            cr.stroke()
            
        elif self.current_tool == 'circle':
            cr.save()
            cr.translate(x + w/2, y + h/2)
            cr.scale(w/2, h/2)
            cr.arc(0, 0, 1, 0, 2 * math.pi)
            cr.restore()
            if self.fill_active:
                cr.fill_preserve()
            cr.stroke()

        elif self.current_tool == 'line':
            cr.move_to(self.start_x, self.start_y)
            cr.line_to(self.last_x, self.last_y)
            cr.stroke()

        elif self.current_tool == 'arrow':
            self.draw_arrow(cr, self.start_x, self.start_y, self.last_x, self.last_y)

    def commit_shape(self, end_x, end_y):
        # Commit the shape to the permanent surface
        cr = cairo.Context(self.surface)
        x = min(self.start_x, end_x)
        y = min(self.start_y, end_y)
        w = abs(self.start_x - end_x)
        h = abs(self.start_y - end_y)
        
        self.apply_style(cr)
        
        if self.current_tool == 'rectangle':
            cr.rectangle(x, y, w, h)
            if self.fill_active:
                cr.fill_preserve()
            cr.stroke()
            
        elif self.current_tool == 'circle':
            cr.save()
            cr.translate(x + w/2, y + h/2)
            cr.scale(w/2, h/2)
            cr.arc(0, 0, 1, 0, 2 * math.pi)
            cr.restore()
            if self.fill_active:
                cr.fill_preserve()
            cr.stroke()

        elif self.current_tool == 'line':
            cr.move_to(self.start_x, self.start_y)
            cr.line_to(end_x, end_y)
            cr.stroke()

        elif self.current_tool == 'arrow':
            self.draw_arrow(cr, self.start_x, self.start_y, end_x, end_y)
            
        self.queue_draw()

    def apply_crop(self, end_x, end_y):
        x = int(min(self.start_x, end_x))
        y = int(min(self.start_y, end_y))
        w = int(abs(self.start_x - end_x))
        h = int(abs(self.start_y - end_y))
        
        if w < 10 or h < 10: return # Ignore tiny crops
        
        # Create new surface with cropped size
        new_surface = self.get_window().create_similar_surface(
            cairo.CONTENT_COLOR_ALPHA, w, h)
            
        cr = cairo.Context(new_surface)
        cr.set_source_surface(self.surface, -x, -y)
        cr.paint()
        
        self.surface = new_surface
        self.set_size_request(w, h)
        self.queue_draw()
        
        # We should notify parent to resize window? 
        # For now, size request handles widget size, window might stay large.

    def apply_blur(self, end_x, end_y):
        if not self.surface: return
        
        x = int(min(self.start_x, end_x))
        y = int(min(self.start_y, end_y))
        w = int(abs(self.start_x - end_x))
        h = int(abs(self.start_y - end_y))
        
        if w < 5 or h < 5: return
        
        # Flush surface
        self.surface.flush()
        
        data = self.surface.get_data()
        width = self.surface.get_width()
        height = self.surface.get_height()
        stride = self.surface.get_stride()
        
        try:
            # Create PIL Image from surface data
            # Cairo ARGB32 is BGRA (on little endian)
            img = Image.frombuffer("RGBA", (width, height), data, "raw", "BGRA", stride, 1)
            
            # Crop
            crop = img.crop((x, y, x+w, y+h))
            
            # Blur
            blurred = crop.filter(ImageFilter.GaussianBlur(radius=10))
            
            # Convert back to BGRA for Cairo
            r, g, b, a = blurred.split()
            bgra = Image.merge("RGBA", (b, g, r, a))
            
            # Get bytes
            buf = bytearray(bgra.tobytes())
            
            # Create temp surface
            tmp_surface = cairo.ImageSurface.create_for_data(
                buf, cairo.FORMAT_ARGB32, w, h, w*4)
            
            # Paint onto main surface
            cr = cairo.Context(self.surface)
            cr.set_source_surface(tmp_surface, x, y)
            cr.paint()
            
            self.queue_draw()
            
        except Exception as e:
            print("Blur error:", e)

    def draw_stroke(self, x, y):
        # Assuming start_x is set
        cr = cairo.Context(self.surface)
        
        if self.current_tool == 'pen':
            self.apply_style(cr)
        elif self.current_tool == 'highlighter':
            color = self.stroke_color
            cr.set_source_rgba(color.red, color.green, color.blue, 0.4 * self.opacity)
            cr.set_line_width(self.line_width)
        elif self.current_tool == 'eraser':
            cr.set_operator(cairo.OPERATOR_CLEAR)
            cr.set_line_width(self.line_width)

        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        
        cr.move_to(self.start_x, self.start_y)
        cr.line_to(x, y)
        cr.stroke()

        if self.current_tool == 'eraser':
            cr.set_operator(cairo.OPERATOR_OVER)
        
        self.queue_draw()

    def get_result_pixbuf(self):
        # Convert surface to pixbuf
        if self.surface:
            width = self.surface.get_width()
            height = self.surface.get_height()
            return Gdk.pixbuf_get_from_surface(self.surface, 0, 0, width, height)
        return self.original_pixbuf
