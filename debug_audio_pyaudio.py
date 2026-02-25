
import pyaudio

def list_devices():
    p = pyaudio.PyAudio()
    print("Available Audio Devices:")
    print("-" * 50)
    
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    
    for i in range(0, numdevices):
        if (p.get_device_info_by_index(i).get('maxInputChannels')) > 0:
            print(f"Input Device ID {i} - {p.get_device_info_by_index(i).get('name')}")
            print(f"  Channels: {p.get_device_info_by_index(i).get('maxInputChannels')}")
            print(f"  Sample Rate: {p.get_device_info_by_index(i).get('defaultSampleRate')}")
            print("-" * 50)

    p.terminate()

if __name__ == "__main__":
    list_devices()
