
import pyaudio
import wave
import numpy as np
import time

# MacBook Pro Microphone is usually index 5 or 0 based on previous logs
# Let's try to find it dynamically
def get_mic_index(p):
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if "Microphone" in info['name']:
            return i
    return -1

def main():
    p = pyaudio.PyAudio()
    
    dev_index = get_mic_index(p)
    if dev_index == -1:
        print("Could not find a microphone!")
        return

    info = p.get_device_info_by_index(dev_index)
    print(f"Opening Microphone: {info['name']} (Index {dev_index})")
    
    RATE = int(info['defaultSampleRate'])
    CHUNK = 1024
    RECORD_SECONDS = 5
    
    stream = p.open(format=pyaudio.paInt16,
                    channels=1, # Mics are usually mono
                    rate=RATE,
                    input=True,
                    input_device_index=dev_index,
                    frames_per_buffer=CHUNK)

    print(f"Recording for {RECORD_SECONDS} seconds... PLEASE SPEAK INTO THE MIC")

    frames = []

    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            
            audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float32)
            rms = np.sqrt(np.mean(np.square(audio_data)))
            db = 20 * np.log10(rms / 32768.0) if rms > 0 else -100.0
            
            if i % 10 == 0:
                print(f"Mic Level: {db:.1f} dB")
        except Exception as e:
            print(f"Error: {e}")
            break

    print("Finished.")
    stream.stop_stream()
    stream.close()
    p.terminate()

if __name__ == "__main__":
    main()
