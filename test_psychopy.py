from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import re
import sys  # For sys.exit()
import os
import pylink  # Uncomment if connecting to EyeLink
from EyeLinkCoreGraphicsPsychoPy import EyeLinkCoreGraphicsPsychoPy
from psychopy import visual, core, event, monitors, gui
import threading
# from PIL import Image  # for preparing the Host backdrop image

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
    
def setup_calibration():
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

setup_calibration()