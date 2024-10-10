from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
import time
import pylink  # For connecting to EyeLink
from EyeLinkCoreGraphicsPsychoPy import EyeLinkCoreGraphicsPsychoPy
from psychopy import visual, monitors, event
import multiprocessing
from multiprocessing import Queue

# Global settings
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
calibration_queue = Queue()
full_screen = True
dummy_mode = False  # Set to True for testing without EyeLink hardware
EYE_HOST_IP = '100.1.1.1'  # IP address of EyeLink host PC
el_tracker = None
edf_filename = None

def ensure_eyelink_connection():
    """Ensure that the EyeLink connection is active; initialize if necessary."""
    global el_tracker
    if dummy_mode:
        print("Running in dummy mode, EyeLink will not be connected")
        el_tracker = None
        return

    if el_tracker is None or not el_tracker.isConnected():
        try:
            el_tracker = pylink.EyeLink(EYE_HOST_IP)
            print("EyeLink connected")
        except RuntimeError as error:
            print(f'Error connecting to EyeLink: {error}')
            raise RuntimeError("Unable to establish EyeLink connection.")

def setup_results_folder(folder='results'):
    """Ensure the results folder exists for storing EDF data files."""
    os.makedirs(folder, exist_ok=True)

def parse_command(command):
    """Parse command strings into command name and argument."""
    match = re.match(r'(\w+)\((.*)\)', command)
    if match:
        return match.group(1), match.group(2).strip('"')
    return command, None


def show_msg(win, text, color, scn_width, wait_for_keypress=True):
    """ Show task instructions on screen"""

    msg = visual.TextStim(win, text,
                          color,
                          wrapWidth=scn_width/2)
    msg.draw()
    win.flip()

    # wait indefinitely, terminates upon any key press
    if wait_for_keypress:
        event.waitKeys()        

def setup_calibration(queue):
    """Set up graphics environment and perform EyeLink calibration."""
    global el_tracker
    try:
        ensure_eyelink_connection()
        el_tracker.setOfflineMode()
        mon = monitors.Monitor('myMonitor', width=53.0, distance=70.0)
        win = visual.Window(fullscr=full_screen, monitor=mon, winType='pyglet', units='pix')
        scn_width, scn_height = win.size

        el_tracker.sendCommand(f'screen_pixel_coords = 0 0 {scn_width - 1} {scn_height - 1}')
        el_tracker.sendMessage(f'DISPLAY_COORDS 0 0 {scn_width - 1} {scn_height - 1}')
        
        genv = EyeLinkCoreGraphicsPsychoPy(el_tracker, win)
        genv.setCalibrationColors((-1, -1, -1), win.color)

        # Use image of fixation circle
        genv.setTargetType('picture')
        genv.setPictureTarget(os.path.join('images', 'fixTarget.bmp'))
        # genv.setTargetType('circle') # display a standard circle fixation point

        pylink.openGraphicsEx(genv)
        
        # Show calibration instructions
        show_msg(win, 'press ENTER twice to calibrate tracker', color=genv.getForegroundColor(), scn_width=scn_width)
        
        el_tracker.doTrackerSetup()
        
        win.close() # Close the PsychoPy window         
        queue.put('calibration_complete')

    except Exception as e:
        print(f"Error during calibration setup: {str(e)}")
        queue.put('calibration_failed')

@app.route('/send_command', methods=['POST', 'OPTIONS'])
def send_command():
    """Flask route to handle incoming EyeLink commands."""
    global el_tracker, edf_filename

    if request.method == 'OPTIONS':
        return build_cors_preflight_response()

    data = request.json
    command = data.get('command')
    if not command:
        return jsonify({'status': 'error', 'message': 'No command provided'}), 400

    command_name, argument = parse_command(command)
    if dummy_mode:
        return simulate_command(command_name, argument)

    try:
        ensure_eyelink_connection()

        if command_name == 'openEDF' and argument:
            edf_filename = f"{argument}.EDF"
            open_edf_file(edf_filename)

        elif command_name == 'configureEyeLink':
            configure_eyelink()

        elif command_name == 'doTrackerSetup':
            calibration_process = multiprocessing.Process(target=setup_calibration, args=(calibration_queue,))
            calibration_process.start()
            calibration_process.join()
            return handle_calibration_status()

        elif command_name == 'stopRecording':
            stop_recording()

        elif command_name == 'logVariables':
            log_trial_variables()

        elif command_name == 'sendMessage' and argument:
            el_tracker.sendMessage(argument)

        elif command_name == 'sendCommand' and argument:
            send_tracker_command(argument)

        elif command_name == 'startRecording' and argument:
            start_recording(argument)

        elif command_name == 'terminateTask':
            terminate_task()

        elif command_name == 'closeEyeLinkConnection':
            close_eyelink_connection()

        else:
            return jsonify({'status': 'error', 'message': f'Unknown command: {command_name}'}), 400

        return jsonify({'status': 'success', 'message': f'Command "{command_name}" executed'}), 200

    except Exception as e:
        print(f"Error executing command {command_name} with argument '{argument}': {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def open_edf_file(filename):
    ensure_eyelink_connection()
    el_tracker.openDataFile(filename)
    script_name = os.path.basename(__file__)
    el_tracker.sendCommand(f'add_file_preamble_text "RECORDED BY {script_name}"')

def configure_eyelink():
    ensure_eyelink_connection()
    el_tracker.setOfflineMode()
    
    # Get EyeLink version
    vstr = el_tracker.getTrackerVersionString()
    eyelink_ver = int(vstr.split()[-1].split('.')[0])            
    print(f'Running experiment on {vstr}, version {eyelink_ver}')

    # Event control for File and Link 
    file_event_flags = 'LEFT,RIGHT,FIXATION,SACCADE,BLINK,MESSAGE,BUTTON,INPUT'
    link_event_flags = 'LEFT,RIGHT,FIXATION,SACCADE,BLINK,BUTTON,FIXUPDATE,INPUT'
    
    if eyelink_ver > 3:
        file_sample_flags = 'LEFT,RIGHT,GAZE,HREF,RAW,AREA,HTARGET,GAZERES,BUTTON,STATUS,INPUT'
        link_sample_flags = 'LEFT,RIGHT,GAZE,GAZERES,AREA,HTARGET,STATUS,INPUT'
    else:
        file_sample_flags = 'LEFT,RIGHT,GAZE,HREF,RAW,AREA,GAZERES,BUTTON,STATUS,INPUT'
        link_sample_flags = 'LEFT,RIGHT,GAZE,GAZERES,AREA,STATUS,INPUT'

    el_tracker.sendCommand('file_event_filter = ' + file_event_flags)
    el_tracker.sendCommand('file_sample_data = ' + file_sample_flags)
    el_tracker.sendCommand('link_event_filter = ' + link_event_flags)
    el_tracker.sendCommand('link_sample_data = ' + link_sample_flags)

    # Set Sample rate, 250, 500, 1000, or 2000, check your tracker specification
    if eyelink_ver > 2:
        el_tracker.sendCommand('sample_rate = 1000')

    # Choose a calibration type, H3, HV3, HV5, HV13 (HV = horizontal/vertical),
    el_tracker.sendCommand('calibration_type = HV9')

    # Set Event Detection Thresholds
    el_tracker.sendCommand('saccade_velocity_threshold = 35')
    el_tracker.sendCommand('saccade_acceleration_threshold = 9500')   

def stop_recording():
    ensure_eyelink_connection()
    el_tracker.stopRecording()
    el_tracker.sendMessage(f'TRIAL_RESULT {pylink.TRIAL_OK}')

def log_trial_variables():
    ensure_eyelink_connection()
    el_tracker.sendMessage(f'!V TRIAL_VAR condition')

def send_tracker_command(command):
    ensure_eyelink_connection()
    el_tracker.setOfflineMode()
    el_tracker.sendCommand(command)

def start_recording(trial_id):
    ensure_eyelink_connection()
    el_tracker.setOfflineMode()
    el_tracker.sendMessage(f'TRIALID {trial_id}')
    el_tracker.startRecording(1, 1, 1, 1)

def terminate_task():
    ensure_eyelink_connection()
    if edf_filename:
        el_tracker.closeDataFile()
        print('Transferring EDF data file...')
        el_tracker.receiveDataFile(edf_filename, os.path.join('./results', edf_filename))
        print('Completed transferring EDF data file')

def close_eyelink_connection():
    ensure_eyelink_connection()
    el_tracker.close()

def build_cors_preflight_response():
    response = jsonify({'status': 'success'})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
    return response, 200

def simulate_command(command_name, argument):
    print(f"Simulated sending command: {command_name} with argument '{argument}'")
    return jsonify({'status': 'success', 'message': f'Command "{command_name}" simulated in dummy mode'}), 200

def handle_calibration_status():
    status = calibration_queue.get()
    if status == 'calibration_complete':
        return jsonify({'status': 'success', 'message': 'Calibration completed'}), 200
    return jsonify({'status': 'error', 'message': 'Calibration failed'}), 500

if __name__ == '__main__':
    setup_results_folder()
    ensure_eyelink_connection()
    app.run(host='127.0.0.1', port=5000, threaded=False)
