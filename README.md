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
