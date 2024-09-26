from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import re
import sys  # For sys.exit()
# import pylink  # Uncomment if connecting to EyeLink

dummy_mode = True

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes, allowing all origins by default

EYE_HOST_IP = '100.1.1.1'

if dummy_mode:
    print("Running in dummy mode, EyeLink will not be connected")
    el_tracker = None
else:
    try:
        # Uncomment when not in dummy mode
        # el_tracker = pylink.EyeLink(EYE_HOST_IP)
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
                    try:
                        el_tracker.openDataFile(edf_file)
                    except RuntimeError as err:
                        print(f'Error opening EDF file: {err}')
                        # Close the EyeLink connection if it exists
                        if el_tracker.isConnected():
                            el_tracker.close()
                                                
                        sys.exit()  # Exit the program
                elif command_name == 'doTrackerSetup':
                    el_tracker.doTrackerSetup()  
                elif command_name == 'startRecording':
                    el_tracker.startRecording(1, 1, 1, 1)  
                elif command_name == 'stopRecording':
                    el_tracker.stopRecording()  
                elif command_name == 'sendMessage' and argument:
                    el_tracker.sendMessage(argument)  
                elif command_name == 'sendCommand' and argument:
                    el_tracker.sendCommand(argument)  
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
    app.run(host='0.0.0.0', port=5000)

