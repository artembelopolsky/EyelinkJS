EyelinkJS project

Testet with python 3.11.0

### Installation
1. Create a virtual environment, activate it and install the requirements
```
pip install -r requirements.txt
```
2. Install pylink manually by copying the *pylink* folder provided by EyeLink to ./my_venv/Lib/site-packages/
Make sure that you copy the correct version of *pylink*, corresponding to your python version and machine type (x64)

3. Start *flask* proxy server in the terminal
```
python my_python_server
```

4. Start local python server in another terminal
```
python -m http.server
```

5. Go to localhost:8000 in your browser and send test commands to EyeLink


### Testing
To test the EyeLinkJS API you can enter the following commands in the "send command" dialogbox in the browser:

1. openEDF(myfile) -- opens myfile.edf on the EyeLink host computer

2. configureEyeLink() -- runs configuration settings for your desired setup (such sampling rate, events to store, saccade detection algorithm parameters)


