"""
Video Engine Module
Handles screen recording using MSS and OpenCV.
"""

import cv2
import numpy as np
import mss
import threading
import time
import os
from datetime import datetime
from typing import Optional, Tuple
from enum import Enum

class VideoState(Enum):
    """Video recording state."""
    STOPPED = "stopped"
    RECORDING = "recording"

class VideoEngine:
    """
    Engine for recording the screen.
    Uses MSS for fast screen capture and OpenCV for writing video files.
    """
    
    def __init__(self):
        """Initialize the video engine."""
        self._state = VideoState.STOPPED
        self._stop_event = threading.Event()
        self._recording_thread: Optional[threading.Thread] = None
        self._output_path: Optional[str] = None
        self._temp_path: Optional[str] = None
        
        # Recording settings
        self.fps = 15.0  # Sufficient for meetings, keeps CPU usage reasonable
        self.screen_size: Optional[Tuple[int, int]] = None
        
    def get_monitors(self) -> list[dict]:
        """
        Get list of available monitors.
        Returns list of dicts with keys 'left', 'top', 'width', 'height'.
        Index 0 in return list corresponds to Monitor 1 (mss index 1).
        """
        monitors = []
        with mss.mss() as sct:
            # sct.monitors[0] is "All Monitors" combined.
            # sct.monitors[1] is Primary, [2] is Secondary, etc.
            # We skip [0] and return the rest.
            if len(sct.monitors) > 1:
                monitors = sct.monitors[1:]
            else:
                monitors = sct.monitors # Fallback if something weird happens
        return monitors

    def start_recording(self, output_dir: str = ".", monitor_index: int = 0) -> bool:
        """
        Start screen recording.
        
        Args:
            output_dir: Directory to save the temp video file.
            monitor_index: Index of the monitor to record (0-based index from get_monitors).
                           This maps to mss monitor index = monitor_index + 1.
            
        Returns:
            True if started successfully.
        """
        if self._state == VideoState.RECORDING:
            return True
            
        try:
            # Prepare output path
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._temp_path = os.path.join(output_dir, f"video_temp_{timestamp}.mp4")
            
            # Start recording thread
            self._stop_event.clear()
            self._state = VideoState.RECORDING
            
            # Map 0-based index to mss 1-based index (1=Primary)
            mss_index = monitor_index + 1
            
            self._recording_thread = threading.Thread(
                target=self._recording_loop, 
                args=(mss_index,), 
                daemon=True
            )
            self._recording_thread.start()
            
            return True
            
        except Exception as e:
            print(f"Failed to start video recording: {e}")
            self._state = VideoState.STOPPED
            return False

    def stop_recording(self) -> Optional[str]:
        """
        Stop recording and return the path to the video file.
        
        Returns:
            Path to the temporary video file.
        """
        if self._state == VideoState.STOPPED:
            return None
            
        self._stop_event.set()
        
        if self._recording_thread and self._recording_thread.is_alive():
            self._recording_thread.join(timeout=3.0)
            
        self._state = VideoState.STOPPED
        return self._temp_path

    def _recording_loop(self, mss_index: int) -> None:
        """Main recording loop."""
        video_writer = None
        
        with mss.mss() as sct:
            # Validate index
            if mss_index >= len(sct.monitors):
                print(f"Invalid monitor index {mss_index}, defaulting to 1")
                mss_index = 1
                
            monitor = sct.monitors[mss_index]
            width = monitor["width"]
            height = monitor["height"]
            
            # Initialize Video Writer
            # mp4v is generally widely supported
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            
            # Handle Retina/High-DPI displays
            # If width > 1920, downscale by 50% to save space/CPU
            scale_factor = 1.0
            if width > 1920:
                scale_factor = 0.5
                
            target_width = int(width * scale_factor)
            target_height = int(height * scale_factor)
            
            video_writer = cv2.VideoWriter(
                self._temp_path,
                fourcc,
                self.fps,
                (target_width, target_height)
            )
            
            frame_duration = 1.0 / self.fps
            
            while not self._stop_event.is_set():
                start_time = time.time()
                
                try:
                    # Capture screen
                    img = sct.grab(monitor)
                    
                    # Convert to numpy array
                    frame = np.array(img)
                    
                    # MSS returns BGRA, OpenCV needs BGR
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    
                    # Resize if needed
                    if scale_factor != 1.0:
                        frame = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)
                    
                    # Write frame
                    if video_writer:
                        video_writer.write(frame)
                        
                except Exception as e:
                    print(f"Frame capture error: {e}")
                
                # Maintain FPS
                elapsed = time.time() - start_time
                wait_time = max(0, frame_duration - elapsed)
                time.sleep(wait_time)
                
            # Cleanup
            if video_writer:
                video_writer.release()
