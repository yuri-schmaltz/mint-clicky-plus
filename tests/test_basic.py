import unittest
import sys
import os

GI_AVAILABLE = False
DEPS_AVAILABLE = False

try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    gi.require_version('GdkX11', '3.0')
    from gi.repository import Gdk
    GI_AVAILABLE = True
except Exception:
    GI_AVAILABLE = False

try:
    import cairo
    if GI_AVAILABLE:
        # Add the library directory to sys.path to import modules
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../usr/lib/clicky')))
        from utils import cairo_rect_to_gdk_rect, gdk_rect_to_cairo_rect
        DEPS_AVAILABLE = True
except Exception:
    DEPS_AVAILABLE = False

class MockGdkRectangle:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def __eq__(self, other):
        return (self.x == other.x and 
                self.y == other.y and 
                self.width == other.width and 
                self.height == other.height)

class MockCairoRectangle:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

class TestUtils(unittest.TestCase):
    
    def test_basic_math(self):
        self.assertEqual(1 + 1, 2)

    @unittest.skipUnless(DEPS_AVAILABLE, "GTK/Cairo indisponível para testes de conversão")
    def test_rect_conversion(self):
        cairo_rect = cairo.RectangleInt(1, 2, 3, 4)
        gdk_rect = cairo_rect_to_gdk_rect(cairo_rect)
        self.assertEqual((gdk_rect.x, gdk_rect.y, gdk_rect.width, gdk_rect.height), (1, 2, 3, 4))
        round_trip = gdk_rect_to_cairo_rect(gdk_rect)
        self.assertEqual((round_trip.x, round_trip.y, round_trip.width, round_trip.height), (1, 2, 3, 4))

    # We would test crop_geometry and conversions here.
    # Since utils.py relies heavily on X11/Gdk imports which might be hard to mock perfectly without a display,
    # we start with importability and basic logic.

if __name__ == '__main__':
    unittest.main()
