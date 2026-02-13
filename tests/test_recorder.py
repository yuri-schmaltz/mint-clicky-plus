import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "usr/lib/clicky"))
from recorder import ScreenRecorder

class TestScreenRecorder(unittest.TestCase):
    @patch("subprocess.Popen")
    def test_start_webm(self, mock_popen):
        recorder = ScreenRecorder()
        output = "/tmp/test.webm"
        recorder.start(0, 0, 1920, 1080, output, "webm")
        
        args = mock_popen.call_args[0][0]
        self.assertIn("ffmpeg", args)
        self.assertIn("-f", args)
        self.assertIn("x11grab", args)
        self.assertIn("1920x1080", args)
        self.assertIn("libvpx-vp9", args)
        self.assertEqual(recorder.output_file, output)

    @patch("subprocess.Popen")
    def test_start_gif(self, mock_popen):
        recorder = ScreenRecorder()
        output = "/tmp/test.gif"
        recorder.start(100, 100, 500, 500, output, "gif")
        
        args = mock_popen.call_args[0][0]
        self.assertTrue(args[-1].endswith(".gif"))
        self.assertTrue(any("scale=" in arg for arg in args))

    @patch("os.getpgid")
    @patch("os.killpg")
    def test_stop(self, mock_killpg, mock_getpgid):
        recorder = ScreenRecorder()
        recorder.process = MagicMock()
        recorder.process.pid = 12345
        recorder.output_file = "/tmp/out.webm"
        
        mock_getpgid.return_value = 12345
        
        path = recorder.stop()
        self.assertEqual(path, "/tmp/out.webm")
        self.assertIsNone(recorder.process)
        mock_killpg.assert_called()

if __name__ == '__main__':
    unittest.main()
