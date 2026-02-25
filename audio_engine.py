"""
Audio Engine Module
Handles audio device detection and recording stream management.
"""

import pyaudio
import numpy as np
import wave
import threading
import os
import time
from datetime import datetime
from typing import Optional, List, Dict, Callable, Any
from dataclasses import dataclass
from enum import Enum

from silence_detector import SilenceDetector
from noise_gate import NoiseGate


class RecordingState(Enum):
    """Recording state enumeration."""
    STOPPED = "stopped"
    RECORDING = "recording"
    PAUSED = "paused"


@dataclass
class AudioDevice:
    """Represents an audio input device."""
    index: int
    name: str
    max_input_channels: int
    default_sample_rate: int
    is_blackhole: bool = False


class AudioEngine:
    """
    Core audio engine for recording from system audio devices.
    Integrates with BlackHole virtual audio driver.
    """
    
    # Audio configuration
    FORMAT = pyaudio.paInt16
    CHANNELS = 2
    SAMPLE_RATE = 22050  # Reduced from 44100 for smaller files
    CHUNK_SIZE = 1024
    
    def __init__(self):
        """Initialize the audio engine."""
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._state = RecordingState.STOPPED
        self._recording_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Audio buffers
        self._audio_frames: List[bytes] = []
        self._current_chunk: Optional[np.ndarray] = None
        self._mic_stream: Optional[pyaudio.Stream] = None
        self._mic_channels: int = 2
        
        # Silence detection
        # Using -55dB threshold to match level meter's visual range (-60 to 0dB)
        # Any audio visible on the meter should NOT trigger silence warning
        self.sys_silence_detector = SilenceDetector(
            silence_threshold_db=-55.0,
            silence_duration_threshold=3.0,
            sample_rate=self.SAMPLE_RATE
        )
        
        self.mic_silence_detector = SilenceDetector(
            silence_threshold_db=-55.0,
            silence_duration_threshold=3.0,
            sample_rate=self.SAMPLE_RATE
        )
        
        # Callbacks
        self._level_callback: Optional[Callable[[float, float], None]] = None
        self._silence_callback: Optional[Callable[[bool, float, bool, float], None]] = None
        self._error_callback: Optional[Callable[[str], None]] = None
        
        # Mic gain (1.0 = unity, 0.5 = -6dB, 2.0 = +6dB)
        self._mic_gain: float = 1.0
        
        # Noise gate for mic
        self._noise_gate = NoiseGate(
            threshold_db=-40.0,
            attack_ms=5.0,
            release_ms=50.0,
            hold_ms=100.0,
            sample_rate=self.SAMPLE_RATE
        )
        self._noise_gate_enabled: bool = False
        
        # Recording info
        self._output_path: Optional[str] = None
        self._wav_path: Optional[str] = None
        self._recording_start_time: Optional[datetime] = None
        self._selected_device_index: Optional[int] = None
        
    def initialize(self) -> bool:
        """
        Initialize PyAudio.
        
        Returns:
            True if initialization successful.
        """
        try:
            self._pyaudio = pyaudio.PyAudio()
            return True
        except Exception as e:
            if self._error_callback:
                self._error_callback(f"Failed to initialize audio: {e}")
            return False
    
    def terminate(self) -> None:
        """Clean up PyAudio resources."""
        self.stop_recording()
        if self._pyaudio:
            self._pyaudio.terminate()
            self._pyaudio = None
    
    def get_input_devices(self) -> List[AudioDevice]:
        """
        Get list of available audio input devices.
        
        Returns:
            List of AudioDevice objects.
        """
        if not self._pyaudio:
            return []
        
        devices = []
        device_count = self._pyaudio.get_device_count()
        
        for i in range(device_count):
            try:
                info = self._pyaudio.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    name = info['name']
                    is_blackhole = 'blackhole' in name.lower()
                    
                    device = AudioDevice(
                        index=i,
                        name=name,
                        max_input_channels=int(info['maxInputChannels']),
                        default_sample_rate=int(info['defaultSampleRate']),
                        is_blackhole=is_blackhole
                    )
                    devices.append(device)
            except Exception:
                continue
        
        return devices
    
    def find_blackhole_device(self) -> Optional[AudioDevice]:
        """
        Find the BlackHole audio device.
        
        Returns:
            BlackHole AudioDevice if found, None otherwise.
        """
        devices = self.get_input_devices()
        for device in devices:
            if device.is_blackhole:
                return device
        return None
    
    def set_level_callback(self, callback: Callable[[float, float], None]) -> None:
        """Set callback for audio level updates (receives sys_db, mic_db)."""
        self._level_callback = callback
    
    def set_silence_callback(self, callback: Callable[[bool, float, bool, float], None]) -> None:
        """Set callback for silence detection (receives sys_warn, sys_dur, mic_warn, mic_dur)."""
        self._silence_callback = callback
    
    def set_error_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for error messages."""
        self._error_callback = callback
    
    def start_recording(self, device_index: int, output_dir: str = ".", mic_device_index: Optional[int] = None) -> bool:
        """
        Start recording from the specified device(s).
        
        Args:
            device_index: Index of the primary audio input device.
            output_dir: Directory to save recordings.
            mic_device_index: Optional index of secondary microphone device.
            
        Returns:
            True if recording started successfully.
        """
        if self._state == RecordingState.RECORDING:
            return True
        
        if not self._pyaudio:
            if not self.initialize():
                return False
        
        try:
            # Create output directory if needed
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate output filename with timestamp (MP3 format)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._wav_path = os.path.join(output_dir, f"recording_{timestamp}.wav")
            self._output_path = os.path.join(output_dir, f"recording_{timestamp}.mp3")
            
            # 1. Open microphone stream FIRST if selected
            # This handles Bluetooth devices (AirPods) that switch profiles (A2DP -> HFP)
            # when the mic is activated, which would kill an existing BlackHole stream.
            if mic_device_index is not None:
                try:
                    # Check device capabilities
                    mic_info = self._pyaudio.get_device_info_by_index(mic_device_index)
                    max_mic_channels = int(mic_info.get('maxInputChannels', 1))
                    
                    # Use device channels, but max of 2 (we don't support >2 mixing yet)
                    self._mic_channels = min(2, max_mic_channels)
                    
                    self._mic_stream = self._pyaudio.open(
                        format=self.FORMAT,
                        channels=self._mic_channels,
                        rate=self.SAMPLE_RATE,
                        input=True,
                        input_device_index=mic_device_index,
                        frames_per_buffer=self.CHUNK_SIZE
                    )
                    
                    # Wait a bit for the audio system to settle after profile switch
                    time.sleep(0.5)
                    
                except Exception as e:
                    if self._error_callback:
                        self._error_callback(f"Failed to open microphone: {e}\nContinuing with system audio only.")
                    self._mic_stream = None

            # 2. Open primary audio stream (BlackHole)
            self._stream = self._pyaudio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.CHUNK_SIZE
            )
            
            # Reset state
            self._audio_frames = []
            self._selected_device_index = device_index
            self._recording_start_time = datetime.now()
            self._stop_event.clear()
            self.sys_silence_detector.reset()
            self.mic_silence_detector.reset()
            self._noise_gate.reset()
            
            # Start recording thread
            self._state = RecordingState.RECORDING
            self._recording_thread = threading.Thread(target=self._recording_loop, daemon=True)
            self._recording_thread.start()
            
            return True
            
        except Exception as e:
            if self._error_callback:
                self._error_callback(f"Failed to start recording: {e}")
            self._state = RecordingState.STOPPED
            return False
    
    def stop_recording(self) -> Optional[str]:
        """
        Stop recording and save to file.
        
        Returns:
            Path to saved file, or None if no recording.
        """
        if self._state == RecordingState.STOPPED:
            return None
        
        # Signal thread to stop
        self._stop_event.set()
        self._state = RecordingState.STOPPED
        
        # Wait for thread to finish
        if self._recording_thread and self._recording_thread.is_alive():
            self._recording_thread.join(timeout=2.0)
        
        # Close stream
        for stream in [self._stream, self._mic_stream]:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
        
        self._stream = None
        self._mic_stream = None
        
        # Save the recording
        output_path = self._save_recording()
        
        return output_path
    
    def pause_recording(self) -> None:
        """Pause the current recording."""
        if self._state == RecordingState.RECORDING:
            self._state = RecordingState.PAUSED
    
    def resume_recording(self) -> None:
        """Resume a paused recording."""
        if self._state == RecordingState.PAUSED:
            self._state = RecordingState.RECORDING
    
    def _recording_loop(self) -> None:
        """Main recording loop (runs in separate thread)."""
        while not self._stop_event.is_set():
            if self._state == RecordingState.PAUSED:
                time.sleep(0.01)  # Avoid busy-wait when paused
                continue
            
            try:
                # Read audio data from primary source
                data = self._stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                
                # Convert to numpy for processing
                sys_array = np.frombuffer(data, dtype=np.int16).astype(np.int32)
                
                # Process System Audio Silence
                _, sys_warning, sys_duration = self.sys_silence_detector.process_chunk(
                    sys_array.astype(np.int16), self.CHUNK_SIZE
                )
                
                # Prepare mixed array (start with system audio)
                mixed_array = sys_array
                
                # Initialize mic status (default to no warning if not active)
                mic_warning = False
                mic_duration = 0.0
                mic_db = -100.0
                has_mic_data = False
                
                # Read and mix microphone if available
                if self._mic_stream:
                    try:
                        mic_data = self._mic_stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                        mic_array = np.frombuffer(mic_data, dtype=np.int16).astype(np.int32)
                        
                        # Handle Mono Mic -> Stereo Output
                        if self._mic_channels == 1:
                            mic_array = np.column_stack((mic_array, mic_array)).flatten()
                        
                        # Apply noise gate if enabled
                        if self._noise_gate_enabled:
                            mic_array = self._noise_gate.process(mic_array.astype(np.int16)).astype(np.int32)
                        
                        # Apply mic gain
                        if self._mic_gain != 1.0:
                            mic_array = (mic_array * self._mic_gain).astype(np.int32)
                            
                        # Process Mic Silence
                        _, mic_warning, mic_duration = self.mic_silence_detector.process_chunk(
                            mic_array.astype(np.int16), self.CHUNK_SIZE
                        )
                        
                        # Calculate mic level for meters
                        mic_rms = self.mic_silence_detector.calculate_rms(mic_array)
                        mic_db = self.mic_silence_detector.rms_to_db(mic_rms)
                        has_mic_data = True
                        
                        # Mix audio (simple addition)
                        if len(mic_array) == len(mixed_array):
                            mixed_array = mixed_array + mic_array
                            
                    except Exception:
                        pass
                
                # Clip to 16-bit range for saving
                final_audio = np.clip(mixed_array, -32768, 32767).astype(np.int16)
                
                # Store mixed audio
                self._audio_frames.append(final_audio.tobytes())
                
                # Calculate system level
                sys_rms = self.sys_silence_detector.calculate_rms(sys_array)
                sys_db = self.sys_silence_detector.rms_to_db(sys_rms)
                
                # Notify callbacks
                if self._level_callback:
                    self._level_callback(sys_db, mic_db)
                
                if self._silence_callback:
                    self._silence_callback(sys_warning, sys_duration, mic_warning, mic_duration)
                    
            except Exception as e:
                if self._error_callback:
                    self._error_callback(f"Recording error: {e}")
                break
    
    def _save_recording(self) -> Optional[str]:
        """
        Save recorded audio to MP3 file.
        
        Returns:
            Path to saved file, or None if save failed.
        """
        if not self._audio_frames or not self._output_path:
            return None
        
        try:
            # First save as WAV
            with wave.open(self._wav_path, 'wb') as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(self._pyaudio.get_sample_size(self.FORMAT))
                wf.setframerate(self.SAMPLE_RATE)
                wf.writeframes(b''.join(self._audio_frames))
            
            # Convert to MP3 using ffmpeg directly (pydub has Python 3.14 compatibility issues)
            import subprocess
            try:
                result = subprocess.run([
                    'ffmpeg', '-y',  # Overwrite output
                    '-i', self._wav_path,  # Input WAV
                    '-codec:a', 'libmp3lame',  # MP3 codec
                    '-b:a', '128k',  # Bitrate
                    '-loglevel', 'error',  # Only show errors
                    self._output_path  # Output MP3
                ], capture_output=True, text=True)
                
                if result.returncode == 0 and os.path.exists(self._output_path):
                    # Successfully converted, remove WAV
                    os.remove(self._wav_path)
                else:
                    # Conversion failed, keep WAV
                    if self._error_callback and result.stderr:
                        self._error_callback(f"MP3 conversion failed: {result.stderr}")
                    self._output_path = self._wav_path
                    
            except FileNotFoundError:
                # ffmpeg not installed, keep WAV
                if self._error_callback:
                    self._error_callback("ffmpeg not found, saved as WAV. Install with: brew install ffmpeg")
                self._output_path = self._wav_path
            except Exception as e:
                # Other conversion error, keep WAV
                if self._error_callback:
                    self._error_callback(f"MP3 conversion failed, saved as WAV: {e}")
                self._output_path = self._wav_path
            
            return self._output_path
            
        except Exception as e:
            if self._error_callback:
                self._error_callback(f"Failed to save recording: {e}")
            return None
    
    def enable_mic(self, mic_device_index: int) -> bool:
        """Enable microphone stream dynamically during recording."""
        if self._state != RecordingState.RECORDING or not self._pyaudio:
            return False
        
        # Already open
        if self._mic_stream:
            return True
        
        try:
            mic_info = self._pyaudio.get_device_info_by_index(mic_device_index)
            max_mic_channels = int(mic_info.get('maxInputChannels', 1))
            self._mic_channels = min(2, max_mic_channels)
            
            self._mic_stream = self._pyaudio.open(
                format=self.FORMAT,
                channels=self._mic_channels,
                rate=self.SAMPLE_RATE,
                input=True,
                input_device_index=mic_device_index,
                frames_per_buffer=self.CHUNK_SIZE
            )
            return True
        except Exception as e:
            if self._error_callback:
                self._error_callback(f"Failed to open microphone: {e}")
            self._mic_stream = None
            return False
    
    def disable_mic(self) -> None:
        """Disable microphone stream dynamically during recording."""
        if self._mic_stream:
            try:
                self._mic_stream.stop_stream()
                self._mic_stream.close()
            except Exception:
                pass
            self._mic_stream = None
    
    @property
    def mic_gain(self) -> float:
        """Get mic gain multiplier."""
        return self._mic_gain
    
    @mic_gain.setter
    def mic_gain(self, value: float) -> None:
        """Set mic gain (0.0 to 3.0)."""
        self._mic_gain = max(0.0, min(3.0, value))
    
    @property
    def noise_gate_enabled(self) -> bool:
        """Get noise gate enabled state."""
        return self._noise_gate_enabled
    
    @noise_gate_enabled.setter
    def noise_gate_enabled(self, value: bool) -> None:
        """Enable/disable noise gate."""
        self._noise_gate_enabled = value
        if not value:
            self._noise_gate.reset()
    
    @property
    def noise_gate_threshold(self) -> float:
        """Get noise gate threshold in dB."""
        return self._noise_gate.threshold_db
    
    @noise_gate_threshold.setter
    def noise_gate_threshold(self, value: float) -> None:
        """Set noise gate threshold in dB."""
        self._noise_gate.threshold_db = value
    
    @property
    def noise_gate_is_open(self) -> bool:
        """Check if noise gate is currently open."""
        return self._noise_gate.is_open
    
    @property
    def state(self) -> RecordingState:
        """Get current recording state."""
        return self._state
    
    @property
    def recording_duration(self) -> float:
        """Get current recording duration in seconds."""
        if not self._audio_frames:
            return 0.0
        
        total_samples = len(self._audio_frames) * self.CHUNK_SIZE
        return total_samples / self.SAMPLE_RATE
    
    @property
    def output_path(self) -> Optional[str]:
        """Get the output file path."""
        return self._output_path
