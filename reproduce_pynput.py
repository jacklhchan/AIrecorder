from pynput import keyboard
import time

def on_activate():
    print('Global hotkey activated!')

hotkeys = {
    '<cmd>+<shift>+r': on_activate
}

print("Starting GlobalHotKeys listener...")
try:
    with keyboard.GlobalHotKeys(hotkeys) as h:
        print("Listener started. Press Cmd+Shift+R or Wait 5 seconds.")
        time.sleep(5)
except Exception as e:
    print(f"Crashed: {e}")
    import traceback
    traceback.print_exc()
