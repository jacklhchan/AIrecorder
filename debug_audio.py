import sounddevice as sd
import numpy as np
import time

def list_devices():
    print("\n=== Audio Devices ===")
    print(sd.query_devices())
    print("=====================")

def check_blackhole():
    print("\nSearching for 'BlackHole 2ch'...")
    devices = sd.query_devices()
    bh_idx = None
    for i, dev in enumerate(devices):
        if "BlackHole 2ch" in dev['name'] and dev['max_input_channels'] > 0:
            bh_idx = i
            print(f"Found BlackHole 2ch at index {i}")
            break
    
    if bh_idx is None:
        print("ERROR: BlackHole 2ch not found!")
        return

    print(f"\nTesting input from BlackHole 2ch (Index {bh_idx})...")
    print("Please play some audio on your system!")
    
    try:
        def callback(indata, frames, time, status):
            if status:
                print(status)
            volume_norm = np.linalg.norm(indata) * 10
            print(f"RMS: {volume_norm:.4f} | Max: {np.max(indata):.4f}")

        with sd.InputStream(device=bh_idx, channels=2, callback=callback):
            print("Recording... (Press Ctrl+C to stop)")
            time.sleep(5)
            print("Finished.")
            
    except Exception as e:
        print(f"Error opening stream: {e}")

if __name__ == "__main__":
    list_devices()
    check_blackhole()
