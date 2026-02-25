"""
Noise Gate Module
Applies a noise gate to audio data to suppress background noise.
Uses smooth gain ramping to avoid clicks/pops.
"""

import numpy as np
from typing import Optional


class NoiseGate:
    """
    A noise gate that mutes audio below a threshold with smooth transitions.
    
    Features:
        - Configurable threshold, attack, release, hold times
        - Smooth gain ramping to avoid clicks/pops
        - Per-chunk processing for real-time use
    """
    
    def __init__(self,
                 threshold_db: float = -40.0,
                 attack_ms: float = 5.0,
                 release_ms: float = 50.0,
                 hold_ms: float = 100.0,
                 sample_rate: int = 22050):
        """
        Initialize the noise gate.
        
        Args:
            threshold_db: Level below which audio is gated (in dB).
            attack_ms: Time for gate to fully open (ms).
            release_ms: Time for gate to fully close (ms).
            hold_ms: Minimum time gate stays open after signal drops below threshold (ms).
            sample_rate: Audio sample rate.
        """
        self.threshold_db = threshold_db
        self.sample_rate = sample_rate
        
        # Convert times to sample counts
        self._attack_samples = max(1, int(attack_ms * sample_rate / 1000))
        self._release_samples = max(1, int(release_ms * sample_rate / 1000))
        self._hold_samples = max(1, int(hold_ms * sample_rate / 1000))
        
        # State
        self._gain = 0.0  # Current gain (0.0 = closed, 1.0 = open)
        self._hold_counter = 0  # Samples remaining in hold period
        self._is_open = False
        
    @property
    def is_open(self) -> bool:
        """Whether the gate is currently open."""
        return self._is_open
    
    def reset(self) -> None:
        """Reset gate state."""
        self._gain = 0.0
        self._hold_counter = 0
        self._is_open = False
    
    def _rms_to_db(self, rms: float, reference: float = 32768.0) -> float:
        """Convert RMS to dB."""
        if rms <= 0:
            return -100.0
        return 20 * np.log10(rms / reference)
    
    def process(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Process audio through the noise gate.
        
        Args:
            audio_data: Audio samples as int16 numpy array.
            
        Returns:
            Gated audio as int16 numpy array.
        """
        if len(audio_data) == 0:
            return audio_data
        
        # Calculate RMS of the chunk
        float_data = audio_data.astype(np.float32)
        rms = np.sqrt(np.mean(np.square(float_data)))
        db_level = self._rms_to_db(rms)
        
        # Determine target gain
        signal_above_threshold = db_level >= self.threshold_db
        
        if signal_above_threshold:
            target_gain = 1.0
            self._hold_counter = self._hold_samples
            self._is_open = True
        elif self._hold_counter > 0:
            # Still in hold period
            target_gain = 1.0
            self._hold_counter -= len(audio_data)
            self._is_open = True
        else:
            target_gain = 0.0
            self._is_open = False
        
        # Apply smooth gain ramping
        if target_gain > self._gain:
            # Opening — use attack time
            step = 1.0 / self._attack_samples
            ramp_samples = min(len(float_data), int((target_gain - self._gain) / step))
        else:
            # Closing — use release time
            step = -1.0 / self._release_samples
            ramp_samples = min(len(float_data), int((self._gain - target_gain) / abs(step)))
        
        if ramp_samples > 0 and abs(target_gain - self._gain) > 0.001:
            # Create gain envelope
            gains = np.linspace(self._gain, target_gain, len(float_data))
            result = (float_data * gains).astype(np.int16)
            self._gain = target_gain
        else:
            # Constant gain
            self._gain = target_gain
            result = (float_data * self._gain).astype(np.int16)
        
        return result
