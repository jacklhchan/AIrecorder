
import pyaudio
import wave
import numpy as np
import time

DEVICE_INDEX = 4  # BlackHole 2ch from previous check
RATE = 44100
CHUNK = 1024
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "test_blackhole.wav"

def main():
    p = pyaudio.PyAudio()
    
    # Double check device name
    info = p.get_device_info_by_index(DEVICE_INDEX)
    print(f"Opening Device {DEVICE_INDEX}: {info['name']}")
    
    stream = p.open(format=pyaudio.paInt16,
                    channels=2,
                    rate=RATE,
                    input=True,
                    input_device_index=DEVICE_INDEX,
                    frames_per_buffer=CHUNK)

    print(f"Recording for {RECORD_SECONDS} seconds...")

    frames = []

    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            
            # Helper to show if ANY audio is present
            audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float32)
            rms = np.sqrt(np.mean(np.square(audio_data)))
            db = 20 * np.log10(rms / 32768.0) if rms > 0 else -100.0
            
            if i % 10 == 0:
                print(f"Level: {db:.1f} dB")
        except Exception as e:
            print(f"Error reading stream: {e}")
            break

    print("Finished recording.")

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(2)
    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    print(f"Saved to {WAVE_OUTPUT_FILENAME}")

if __name__ == "__main__":
    main()
