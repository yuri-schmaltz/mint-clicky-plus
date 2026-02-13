import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "usr/lib/clicky"))
from clicky import MyApplication

class TestCLI(unittest.TestCase):
    def test_options_parsing_area(self):
        app = MyApplication("org.x.test", 0)
        # Mock GLib.VariantDict as returned by command_line.get_options_dict()
        mock_options = MagicMock()
        mock_options.contains.side_effect = lambda k: k == "area"
        
        mock_command_line = MagicMock()
        mock_command_line.get_options_dict.return_value = mock_options
        
        with patch.object(MyApplication, 'activate', return_value=None):
            app.do_command_line(mock_command_line)
            self.assertEqual(app.cli_mode, "area")

    def test_options_parsing_screen(self):
        app = MyApplication("org.x.test", 0)
        mock_options = MagicMock()
        mock_options.contains.side_effect = lambda k: k == "screen"
        
        mock_command_line = MagicMock()
        mock_command_line.get_options_dict.return_value = mock_options
        
        with patch.object(MyApplication, 'activate', return_value=None):
            app.do_command_line(mock_command_line)
            self.assertEqual(app.cli_mode, "screen")

if __name__ == '__main__':
    unittest.main()
