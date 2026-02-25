"""
Silence Detector Module
Detects silence in audio streams using RMS level analysis.
"""

import numpy as np
from typing import Tuple


class SilenceDetector:
    """Detects silence in audio data using RMS (Root Mean Square) level analysis."""
    
    def __init__(self, 
                 silence_threshold_db: float = -40.0,
                 silence_duration_threshold: float = 3.0,
                 sample_rate: int = 44100):
        """
        Initialize the silence detector.
        
        Args:
            silence_threshold_db: Audio level below this (in dB) is considered silence.
            silence_duration_threshold: Seconds of continuous silence before warning.
            sample_rate: Sample rate of the audio stream.
        """
        self.silence_threshold_db = silence_threshold_db
        self.silence_duration_threshold = silence_duration_threshold
        self.sample_rate = sample_rate
        
        self._silence_start_time: float = 0.0
        self._total_samples_processed: int = 0
        self._is_silent: bool = False
        self._silence_duration: float = 0.0
    
    def reset(self) -> None:
        """Reset the silence detector state."""
        self._silence_start_time = 0.0
        self._total_samples_processed = 0
        self._is_silent = False
        self._silence_duration = 0.0
    
    def calculate_rms(self, audio_data: np.ndarray) -> float:
        """
        Calculate the RMS (Root Mean Square) of audio data.
        
        Args:
            audio_data: Audio samples as numpy array.
            
        Returns:
            RMS value.
        """
        if len(audio_data) == 0:
            return 0.0
        
        # Convert to float32 for calculation
        data = audio_data.astype(np.float32)
        rms = np.sqrt(np.mean(np.square(data)))
        return rms
    
    def rms_to_db(self, rms: float, reference: float = 32768.0) -> float:
        """
        Convert RMS value to decibels.
        
        Args:
            rms: RMS value.
            reference: Reference value (32768 for 16-bit audio).
            
        Returns:
            Level in decibels.
        """
        if rms <= 0:
            return -100.0  # Return very low dB for silence
        
        db = 20 * np.log10(rms / reference)
        return db
    
    def process_chunk(self, audio_data: np.ndarray, chunk_samples: int) -> Tuple[float, bool, float]:
        """
        Process an audio chunk and detect silence.
        
        Args:
            audio_data: Audio samples as numpy array.
            chunk_samples: Number of samples in this chunk.
            
        Returns:
            Tuple of (db_level, is_warning_active, silence_duration_seconds).
        """
        # Calculate current level
        rms = self.calculate_rms(audio_data)
        db_level = self.rms_to_db(rms)
        
        # Update timing
        current_time = self._total_samples_processed / self.sample_rate
        self._total_samples_processed += chunk_samples
        
        # Check if current chunk is silent
        is_current_silent = db_level < self.silence_threshold_db
        
        if is_current_silent:
            if not self._is_silent:
                # Silence just started
                self._silence_start_time = current_time
                self._is_silent = True
            
            # Calculate silence duration
            self._silence_duration = current_time - self._silence_start_time + (chunk_samples / self.sample_rate)
        else:
            # Audio detected, reset silence state
            self._is_silent = False
            self._silence_duration = 0.0
        
        # Warning is active if silence duration exceeds threshold
        warning_active = self._silence_duration >= self.silence_duration_threshold
        
        return (db_level, warning_active, self._silence_duration)
    
    @property
    def is_warning_active(self) -> bool:
        """Check if silence warning should be displayed."""
        return self._silence_duration >= self.silence_duration_threshold
    
    @property
    def silence_duration(self) -> float:
        """Get current silence duration in seconds."""
        return self._silence_duration
