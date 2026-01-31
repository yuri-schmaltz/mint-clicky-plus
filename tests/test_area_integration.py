import os
import sys
import unittest

RUN_GUI = os.environ.get("CLICKY_RUN_GUI_TESTS") == "1"
HAS_DISPLAY = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

GI_AVAILABLE = False
try:
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    GI_AVAILABLE = True
except Exception:
    GI_AVAILABLE = False

if GI_AVAILABLE:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../usr/lib/clicky")))
    from utils import select_area_interactive


class TestAreaSelectionIntegration(unittest.TestCase):
    @unittest.skipUnless(RUN_GUI and HAS_DISPLAY and GI_AVAILABLE, "Teste manual/GUI opcional")
    def test_select_area_manual(self):
        """Teste manual: selecione uma área na tela para validar retorno."""
        rect = select_area_interactive()
        self.assertIsNotNone(rect)
        self.assertGreater(rect.width, 0)
        self.assertGreater(rect.height, 0)


if __name__ == "__main__":
    unittest.main()
