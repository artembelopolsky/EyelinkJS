
(C) 2024 Artem Belopolsky. All rights reserved. 

EyelinkJS API 

This is an API to operate EyeLink eye-tracker (SR Research) from the browser. The communications from the browser are routed via a local proxy server, running on the Stimulus PC.


Tested with python 3.11.0

### Installation
1. Create a virtual environment, activate it and install the requirements
```
pip install -r requirements.txt
```
2. Install pylink manually by copying the *pylink* folder provided by SR Research to ./my_venv/Lib/site-packages/
Make sure that you copy the correct version of *pylink*, corresponding to your python version and machine type (x64)

3. Add the EyeLinkCoreGraphicsPsychoPy.py provided by SR Research to the main folder

4. Start *flask* proxy server in the terminal
```
python eyelink_server.py
```

5. Start local python server in another terminal
```
python -m http.server
```

6. Go to http://localhost:8000/send_commands.html in your browser and send test commands to EyeLink


### Testing
To test the EyeLinkJS API you can enter the following commands in the "send command" dialogbox in the browser:

1. openEDF(myfile) -- opens myfile.edf on the EyeLink host computer

2. configureEyeLink() -- runs configuration settings for your desired setup (such sampling rate, events to store, saccade detection algorithm parameters)

3. doTrackerSetup() -- this opens psychopy implementation of the camera setup, calibration and validation

4. startRecording(trial_number) -- this will start recording and send a message about the trial number to EDF file

5. sendMessage(text) -- this will send 'text' to EDF file

6. stopRecording() -- this will stop recording

7. terminateTask() -- this will close the EDF file and transfer it to Stimulus PC

8. closeEyeLinkconnection() -- this will close EyeLink connection and you will need to restart the eyelink_server to get it back

9. send_tracker_command(command) -- sends 'command' to EyeLink

10. log_trial_variables(condition, value) -- send a DataViewer readable message to EDF file about the variable you need to log 


