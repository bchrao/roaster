from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import time
import threading
import board
import digitalio
import RPi.GPIO as GPIO
import adafruit_max31855
import json
import os  # <-- Added to check if JSON file exists

# GPIO Configuration
RELAY_PIN = 17
SPI_CLK = board.SCK
SPI_CS = board.D5
SPI_MISO = board.MISO

# Setup Relay Control
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.output(RELAY_PIN, GPIO.LOW)

# Setup Thermocouple (MAX31855)
spi = board.SPI()
cs = digitalio.DigitalInOut(SPI_CS)
thermocouple = adafruit_max31855.MAX31855(spi, cs)

# Flask App with WebSockets
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global Variables
manual_mode = False
heater_on = False
target_temp = None
current_temp = 0
roast_log = []
profiles_file = "profiles.json"

def c_to_f(celsius):
    """Convert Celsius to Fahrenheit."""
    return round((celsius * 9/5) + 32, 2)

def get_temperature():
    """Reads temperature from MAX31855 and converts to Fahrenheit."""
    global current_temp
    try:
        current_temp = c_to_f(thermocouple.temperature)
    except RuntimeError:
        current_temp = None

def monitor_temperature():
    """Continuously monitors temperature and sends updates via WebSockets."""
    while True:
        get_temperature()
        socketio.emit('temperature_update', {'temperature': current_temp})
        time.sleep(2)

def control_heater(state):
    """Turns the heater ON or OFF."""
    global heater_on
    if state and not heater_on:
        print("🔥 Heater ON")
        GPIO.output(RELAY_PIN, GPIO.HIGH)
        heater_on = True
    elif not state and heater_on:
        print("❄️ Heater OFF")
        GPIO.output(RELAY_PIN, GPIO.LOW)
        heater_on = False
    socketio.emit('heater_update', {'heater_on': heater_on})

def manual_control():
    """Handles manual roasting with real-time heater control."""
    global manual_mode, target_temp, roast_log

    print("🚀 Manual mode started")
    roast_log = []  # Reset roast log
    start_time = time.time()

    while manual_mode:
        get_temperature()
        elapsed_time = round(time.time() - start_time, 2)

        # Auto control the heater
        if target_temp is not None:
            if current_temp < target_temp - 5:
                control_heater(True)
            elif current_temp >= target_temp:
                control_heater(False)

        # Log temperature data
        roast_log.append({"time": elapsed_time, "temperature": current_temp})
        socketio.emit('temperature_update', {'temperature': current_temp})

        print(f"🌡️ {elapsed_time}s | Temp: {current_temp}°F | Heater: {'ON' if heater_on else 'OFF'}")
        time.sleep(2)

def run_profile(profile):
    """Execute a saved roasting profile with automatic heater control."""
    global manual_mode, target_temp
    manual_mode = False  # Ensure manual mode is disabled before running profile

    print(f"🚀 Running profile: {profile['name']}")
    for step in profile["steps"]:
        target_temp = step["temperature"]
        print(f"🔥 Target: {target_temp}°F for {step['time']}s")
        step_end_time = time.time() + step["time"]

        while time.time() < step_end_time:
            get_temperature()
            if current_temp < target_temp - 5:
                control_heater(True)
            elif current_temp >= target_temp:
                control_heater(False)

            socketio.emit('temperature_update', {'temperature': current_temp})
            print(f"🌡️ Temp: {current_temp}°F | Heater: {'ON' if heater_on else 'OFF'}")
            time.sleep(2)

    control_heater(False)
    print("✅ Profile completed")
    socketio.emit('profile_complete', {'status': 'Profile Completed'})

def save_profile(name):
    """Save the current roast session as a profile and refresh the profile list."""
    profiles = load_profiles()
    
    # Ensure profile contains roasting steps
    if not roast_log:
        return {"status": "Error: No roasting data to save."}, 400

    profiles[name] = {"name": name, "steps": roast_log}
    save_profiles(profiles)
    
    print(f"✅ Profile '{name}' saved successfully!")  # Debugging output
    return {"status": f"Profile '{name}' saved successfully!"}


def load_profiles():
    """Load roasting profiles from JSON file."""
    if not os.path.exists(profiles_file):  # If file doesn't exist, create an empty one
        save_profiles({})

    try:
        with open(profiles_file, "r") as file:
            profiles = json.load(file)
            print(f"📁 Loaded profiles: {profiles}")  # Debugging output
            return profiles
    except json.JSONDecodeError:
        print("⚠️ Error: Corrupt JSON file! Resetting.")
        save_profiles({})
        return {}

def save_profiles(profiles):
    """Save roasting profiles to JSON file."""
    with open(profiles_file, "w") as file:
        json.dump(profiles, file, indent=4)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/set_manual', methods=['POST'])
def set_manual():
    global manual_mode
    manual_mode = True
    threading.Thread(target=manual_control).start()
    return jsonify({'status': 'Manual mode enabled'})

@app.route('/set_temperature', methods=['POST'])
def set_temperature():
    global target_temp
    target_temp = int(request.form['temperature'])
    return jsonify({'status': f'Target temperature set to {target_temp}°F'})

@app.route('/stop_manual', methods=['POST'])
def stop_roasting():
    """Stop both manual and profile roasting."""
    global manual_mode, target_temp
    manual_mode = False
    target_temp = None  # Reset target temperature
    control_heater(False)  # Turn off the heater

    print("🛑 Roasting stopped manually!")  # Debugging output
    return jsonify({'status': 'Roasting stopped'})


@app.route('/save_profile', methods=['POST'])
def save_profile_api():
    """Save the logged roast session as a profile."""
    profile_name = request.form.get('profile_name')
    if not profile_name:
        return jsonify({'status': 'Error: Profile name is required'}), 400

    save_profile(profile_name)
    return jsonify({'status': f'Roast session saved as {profile_name}'})

@app.route('/get_profiles', methods=['GET'])
def get_profiles():
    """Retrieve and return all saved roasting profiles."""
    profiles = load_profiles()

    if not profiles:
        return jsonify({'status': 'No profiles found', 'profiles': []})

    print(f"📁 Sending profile list: {list(profiles.keys())}")  # Debugging output
    return jsonify({'status': 'Profiles loaded', 'profiles': list(profiles.keys())})


@app.route('/load_profile', methods=['POST'])
def load_profile():
    """Load a saved roasting profile and execute it."""
    profiles = load_profiles()
    profile_name = request.form.get('profile_name')  # Get profile name from the request

    if not profile_name:
        return jsonify({'status': 'Error: Profile name is required'}), 400

    if profile_name not in profiles:
        return jsonify({'status': 'Error: Profile not found'}), 404

    profile = profiles[profile_name]
    print(f"🔍 Loading profile: {profile_name}")  # Debugging output

    # Run the profile in a separate thread
    threading.Thread(target=run_profile, args=(profile,)).start()
    return jsonify({'status': f'Running profile {profile_name}'})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
