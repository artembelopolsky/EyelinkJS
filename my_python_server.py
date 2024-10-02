from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import re
import sys  # For sys.exit()
import os
import pylink  # Uncomment if connecting to EyeLink
from EyeLinkCoreGraphicsPsychoPy import EyeLinkCoreGraphicsPsychoPy
from psychopy import visual, core, event, monitors, gui
import multiprocessing

# Set this variable to True to run the task in full screen mode
# It is easier to debug the script in non-fullscreen mode
full_screen = True

dummy_mode = False

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes, allowing all origins by default

EYE_HOST_IP = '100.1.1.1'

if dummy_mode:
    print("Running in dummy mode, EyeLink will not be connected")
    el_tracker = None
else:
    try:
        # Uncomment when not in dummy mode
        el_tracker = pylink.EyeLink(EYE_HOST_IP)
        pass
    except RuntimeError as error:
        print('ERROR:', error)

def parse_command(command):
    match = re.match(r'(\w+)\((.*)\)', command)
    if match:
        command_name = match.group(1)
        argument = match.group(2).strip('\"')
        return command_name, argument
    else:
        return command, None
    
# def clear_screen(win):
#     """ clear up the PsychoPy window"""

#     win.fillColor = genv.getBackgroundColor()
#     win.flip()

# def abort_trial():
#     """Ends recording """

#     el_tracker = pylink.getEYELINK()

#     # Stop recording
#     if el_tracker.isRecording():
#         # add 100 ms to catch final trial events
#         pylink.pumpDelay(100)
#         el_tracker.stopRecording()

#     # clear the screen
#     clear_screen(win)
#     # Send a message to clear the Data Viewer screen
#     bgcolor_RGB = (116, 116, 116)
#     el_tracker.sendMessage('!V CLEAR %d %d %d' % bgcolor_RGB)

#     # send a message to mark trial end
#     el_tracker.sendMessage('TRIAL_RESULT %d' % pylink.TRIAL_ERROR)

#     return pylink.TRIAL_ERROR

def setup_calibration():
    edf_file = 'avb.EDF'
    print(f'Provided name for EDF file is: {edf_file}')
    try:
        el_tracker.openDataFile(edf_file)
    except RuntimeError as err:
        print(f'Error opening EDF file: {err}')
        # Close the EyeLink connection if it exists
        if el_tracker.isConnected():
            el_tracker.close()

    # Step 4: set up a graphics environment for calibration
    #
    # Open a window, be sure to specify monitor parameters
    mon = monitors.Monitor('myMonitor', width=53.0, distance=70.0)
    win = visual.Window(fullscr=full_screen,
                        monitor=mon,
                        winType='pyglet',
                        units='pix')

    # get the native screen resolution used by PsychoPy
    scn_width, scn_height = win.size
    # # resolution fix for Mac retina displays
    # if 'Darwin' in platform.system():
    #     if use_retina:
    #         scn_width = int(scn_width/2.0)
    #         scn_height = int(scn_height/2.0)

    # Pass the display pixel coordinates (left, top, right, bottom) to the tracker
    # see the EyeLink Installation Guide, "Customizing Screen Settings"
    # el_coords = "screen_pixel_coords = 0 0 %d %d" % (scn_width - 1, scn_height - 1)
    # el_tracker.sendCommand(el_coords)

    # Write a DISPLAY_COORDS message to the EDF file
    # Data Viewer needs this piece of info for proper visualization, see Data
    # Viewer User Manual, "Protocol for EyeLink Data to Viewer Integration"
    # dv_coords = "DISPLAY_COORDS  0 0 %d %d" % (scn_width - 1, scn_height - 1)
    # el_tracker.sendMessage(dv_coords)

    # Configure a graphics environment (genv) for tracker calibration
    genv = EyeLinkCoreGraphicsPsychoPy(el_tracker, win)
    print(genv)  # print out the version number of the CoreGraphics library

    # Set background and foreground colors for the calibration target
    # in PsychoPy, (-1, -1, -1)=black, (1, 1, 1)=white, (0, 0, 0)=mid-gray
    foreground_color = (-1, -1, -1)
    background_color = win.color
    genv.setCalibrationColors(foreground_color, background_color)

    # Set up the calibration target
    #
    # The target could be a "circle" (default), a "picture", a "movie" clip,
    # or a rotating "spiral". To configure the type of calibration target, set
    # genv.setTargetType to "circle", "picture", "movie", or "spiral", e.g.,
    # genv.setTargetType('picture')
    #
    # Use gen.setPictureTarget() to set a "picture" target
    # genv.setPictureTarget(os.path.join('images', 'fixTarget.bmp'))
    #
    # Use genv.setMovieTarget() to set a "movie" target
    # genv.setMovieTarget(os.path.join('videos', 'calibVid.mov'))

    # Use a picture as the calibration target
    genv.setTargetType('circle')
    # genv.setPictureTarget(os.path.join('images', 'fixTarget.bmp'))

    # Configure the size of the calibration target (in pixels)
    # this option applies only to "circle" and "spiral" targets
    # genv.setTargetSize(24)

    # Beeps to play during calibration, validation and drift correction
    # parameters: target, good, error
    #     target -- sound to play when target moves
    #     good -- sound to play on successful operation
    #     error -- sound to play on failure or interruption
    # Each parameter could be ''--default sound, 'off'--no sound, or a wav file
    genv.setCalibrationSounds('', '', '')

    # # resolution fix for macOS retina display issues
    # if use_retina:
    #     genv.fixMacRetinaDisplay()

    # Request Pylink to use the PsychoPy window we opened above for calibration
    pylink.openGraphicsEx(genv)

    el_tracker.doTrackerSetup()
    
    win.close()

@app.route('/send_command', methods=['POST', 'OPTIONS'])
def send_command():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'success'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response, 200

    data = request.json
    command = data.get('command')
    received_time = time.time()

    if command:
        command_name, argument = parse_command(command)

        if dummy_mode:
            print(f"Simulated sending command to EyeLink: {command_name} with argument '{argument}'")
            return jsonify({'status': 'success', 'message': f'Command "{command_name}" with argument "{argument}" simulated as sent to EyeLink'}), 200
        else:
            try:
                # Handle opening an EDF file
                if command_name == 'openEDF' and argument:
                    edf_file = argument + ".EDF"
                    print(f'Provided name for EDF file is: {edf_file}')
                    try:
                        el_tracker.openDataFile(edf_file)
                    except RuntimeError as err:
                        print(f'Error opening EDF file: {err}')
                        # Close the EyeLink connection if it exists
                        if el_tracker.isConnected():
                            el_tracker.close()
                                                
                        sys.exit()  # Exit the program
                elif command_name == 'doTrackerSetup':
                    # Run calibration in a separate processs since it is using psychopy and creates its own window
                    calibration_process = multiprocessing.Process(target=setup_calibration)
                    calibration_process.start()
                    calibration_process.join()
                    print('Calibration started')
                elif command_name == 'startRecording':
                    el_tracker.startRecording(1, 1, 1, 1)  
                    # Allocate some time for the tracker to cache some samples
                    pylink.pumpDelay(100)
                elif command_name == 'stopRecording':
                     # stop recording; add 100 msec to catch final events before stopping
                    pylink.pumpDelay(100)
                    el_tracker.stopRecording()  
                elif command_name == 'sendMessage' and argument:
                    el_tracker.sendMessage(argument)  
                elif command_name == 'sendCommand' and argument:
                    el_tracker.sendCommand(argument)  
                elif command_name == 'startTrial' and argument: # starting every trial, takes trialNr as argument
                    # get a reference to the currently active EyeLink connection
                    el_tracker = pylink.getEYELINK()
                    # put the tracker in the offline mode first
                    el_tracker.setOfflineMode()
                    # send a "TRIALID" message to mark the start of a trial
                    msg_trialID = f'TRIALID {argument}'
                    el_tracker.sendMessage(msg_trialID)
                    # record_status_message : show some info on the Host PC
                    # here we show how many trials has been tested
                    el_tracker.sendCommand("record_status_message '%s'" % msg_trialID)
                    # Start recording
                    # arguments: sample_to_file, events_to_file, sample_over_link,
                    # event_over_link (1-yes, 0-no)
                    try:
                        el_tracker.startRecording(1, 1, 1, 1)
                    except RuntimeError as error:
                        print("ERROR:", error)
                        # abort_trial()
                        return pylink.TRIAL_ERROR

                    # Allocate some time for the tracker to cache some samples
                    pylink.pumpDelay(100)
                elif command_name == 'terminateTask':
                    # Close the edf data file on the Host
                    el_tracker.closeDataFile()
                    # Close the link to the tracker.
                    el_tracker.close()
                else:
                    return jsonify({'status': 'error', 'message': f'Unknown command: {command_name}'}), 400

                send_time = time.time()
                print(f"Command '{command_name}' executed with argument '{argument}'")
                return jsonify({'status': 'success', 'message': f'Command "{command_name}" executed with argument "{argument}"', 
                                'latency': send_time - received_time}), 200
            except Exception as e:
                print(f"Error executing command {command_name} with argument '{argument}': {str(e)}")
                return jsonify({'status': 'error', 'message': str(e)}), 500
    else:
        return jsonify({'status': 'error', 'message': 'No command provided'}), 400

if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=5000)
    app.run(host='127.0.0.1', port=5000, threaded=False)

