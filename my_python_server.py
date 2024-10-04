from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import os
import re
import sys
import pylink  # For connecting to EyeLink
from EyeLinkCoreGraphicsPsychoPy import EyeLinkCoreGraphicsPsychoPy
from psychopy import visual, monitors
import multiprocessing

# Global settings
full_screen = True  # Set to True for full screen, useful for debugging when False
dummy_mode = False  # Set to True for testing without EyeLink hardware
EYE_HOST_IP = '100.1.1.1'  # IP address of EyeLink host PC
el_tracker = None  # Global EyeLink tracker variable
edf_filename = None  # Global variable to store the opened EDF filename

# Flask application setup
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes, allowing all origins by default

def initialize_eyelink():
    """
    Initialize EyeLink connection. If dummy_mode is enabled, EyeLink is not connected.
    """
    global el_tracker
    if dummy_mode:
        print("Running in dummy mode, EyeLink will not be connected")
        el_tracker = None
    else:
        try:
            el_tracker = pylink.EyeLink(EYE_HOST_IP)
            print("EyeLink connected")
        except RuntimeError as error:
            print(f'Error connecting to EyeLink: {error}')

def setup_results_folder():
    """
    Set up a folder to store the EDF data files and the associated resources.
    """
    results_folder = 'results'
    if not os.path.exists(results_folder):
        os.makedirs(results_folder)

# Set up the results folder to store the EDF data files
setup_results_folder()

# Initialize EyeLink tracker at the start
initialize_eyelink()

def parse_command(command):
    """
    Parse a command string and return the command name and argument.
    Command format: command_name(argument)
    
    Args:
        command (str): The command string to be parsed.
    
    Returns:
        tuple: (command_name, argument) where argument is stripped of quotes.
    """
    match = re.match(r'(\w+)\((.*)\)', command)
    if match:
        command_name = match.group(1)
        argument = match.group(2).strip('\"')
        return command_name, argument
    return command, None

def setup_calibration():
    """
    Set up the graphics environment and perform the EyeLink tracker calibration.
    This function opens a PsychoPy window and configures the EyeLink calibration process.
    """
    try:
        # Set up PsychoPy window and monitor parameters
        mon = monitors.Monitor('myMonitor', width=53.0, distance=70.0)
        win = visual.Window(fullscr=full_screen, monitor=mon, winType='pyglet', units='pix')

        # Configure a graphics environment for tracker calibration
        genv = EyeLinkCoreGraphicsPsychoPy(el_tracker, win)
        genv.setCalibrationColors((-1, -1, -1), win.color)  # Set calibration colors
        genv.setTargetType('circle')  # Set calibration target type

        # Use the PsychoPy window for calibration
        pylink.openGraphicsEx(genv)
        el_tracker.doTrackerSetup()  # Run calibration

        win.close()  # Close the PsychoPy window
    except Exception as e:
        print(f"Error during calibration setup: {str(e)}")

@app.route('/send_command', methods=['POST', 'OPTIONS'])
def send_command():
    """
    Flask route to receive and process EyeLink commands.
    """
    global el_tracker, edf_filename

    if request.method == 'OPTIONS':
        response = jsonify({'status': 'success'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response, 200

    data = request.json
    command = data.get('command')
    received_time = time.time()

    if not command:
        return jsonify({'status': 'error', 'message': 'No command provided'}), 400

    command_name, argument = parse_command(command)

    if dummy_mode:
        print(f"Simulated sending command to EyeLink: {command_name} with argument '{argument}'")
        return jsonify({'status': 'success', 'message': f'Command "{command_name}" simulated in dummy mode'}), 200

    try:
        # Ensure EyeLink connection is initialized
        if el_tracker is None:
            initialize_eyelink()

        if command_name == 'openEDF' and argument:
            edf_filename = argument + ".EDF"
            print(f'Opening EDF file: {edf_filename}')
            el_tracker.openDataFile(edf_filename)

        elif command_name == 'doTrackerSetup':
            # Run calibration in a separate process due to PsychoPy window creation
            calibration_process = multiprocessing.Process(target=setup_calibration)
            calibration_process.start()
            calibration_process.join()
            print('Calibration started')

        elif command_name == 'stopRecording':
            try:
                pylink.pumpDelay(100)
                el_tracker.stopRecording()  # Stop recording
            except RuntimeError as error:
                print(f"Error stopping recording: {error}")

        elif command_name == 'sendMessage' and argument:
            try:
                el_tracker.sendMessage(argument)
            except RuntimeError as error:
                print(f"Error sending message: {error}")

        elif command_name == 'sendCommand' and argument:
            try:
                el_tracker.sendCommand(argument)
            except RuntimeError as error:
                print(f"Error sending command: {error}")

        elif command_name == 'startRecording' and argument:
            try:
                # get a reference to the currently active EyeLink connection
                el_tracker = pylink.getEYELINK()

                # Start recording each trial and send TRIALID
                el_tracker.setOfflineMode()
                msg_trialID = f'TRIALID {argument}'
                el_tracker.sendMessage(msg_trialID)
                el_tracker.sendCommand(f"record_status_message '{msg_trialID}'")
                el_tracker.startRecording(1, 1, 1, 1)
                pylink.pumpDelay(100)
            except RuntimeError as error:
                print(f"Error starting recording: {error}")

        elif command_name == 'terminateTask':

            el_tracker = pylink.getEYELINK()  # Get the current active tracker object
            el_tracker.setOfflineMode()
             # Clear the Host PC screen and wait for 500 ms
            el_tracker.sendCommand('clear_screen 0')
            pylink.msecDelay(500)

            if edf_filename:
                try:
                    el_tracker.closeDataFile()  # Close EDF file
                    # Download the EDF data file from the Host PC to a local data folder
                    el_tracker.receiveDataFile(edf_filename, os.path.join('./results', edf_filename))
                except RuntimeError as error:
                    print(f"Error receiving EDF file: {error}")
            else:
                print("No EDF file to download.")
            el_tracker.close()  # Close EyeLink connection

        else:
            return jsonify({'status': 'error', 'message': f'Unknown command: {command_name}'}), 400

        send_time = time.time()
        print(f"Command '{command_name}' executed successfully.")
        return jsonify({'status': 'success', 'message': f'Command "{command_name}" executed with argument "{argument}"',
                        'latency': send_time - received_time}), 200

    except Exception as e:
        print(f"Error executing command {command_name} with argument '{argument}': {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, threaded=False)
