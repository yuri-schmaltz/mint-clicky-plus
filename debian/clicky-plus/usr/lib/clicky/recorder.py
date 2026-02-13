import subprocess
import signal
import os
import time

class ScreenRecorder:
    def __init__(self):
        self.process = None
        self.output_file = None

    def is_recording(self):
        return self.process is not None and self.process.poll() is None

    def start(self, x, y, w, h, output_file, format="webm"):
        if self.is_recording():
            return False
            
        self.output_file = output_file
        
        # Ensure directory
        dirname = os.path.dirname(output_file)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)

        cmd = ["ffmpeg", "-y"]
        
        # Determine backend (simple check)
        # For X11
        layout = f"{w}x{h}"
        offset = f":0.0+{x},{y}"
        
        # Framerate
        fps = 15 if format == "gif" else 30
        
        cmd.extend(["-f", "x11grab", "-video_size", layout, "-framerate", str(fps), "-i", offset])
        
        if format == "gif":
            # GIF settings
            # Using split/palettegen for better quality is possible but slow to start/encode
            # cmd.extend(["-vf", "split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"])
            cmd.extend(["-vf", f"fps={fps},scale='min(800,iw)':-1:flags=lanczos"])
        else:
            # WebM (VP9)
            cmd.extend(["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "30"])
            # cmd.extend(["-pix_fmt", "yuv420p"]) 
            
        cmd.append(output_file)
        
        print("Starting recording:", " ".join(cmd))
        # Use new process group so we can signal it if needed, though terminate() on Popen obj usually works
        self.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.PIPE, preexec_fn=os.setsid)
        return True

    def stop(self):
        if self.process:
            print("Stopping recording...")
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait(timeout=5)
            except Exception as e:
                print("Error stopping recording:", e)
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                except:
                    pass
            self.process = None
            return self.output_file
        return None
