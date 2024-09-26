from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# Enable CORS for all routes, allowing all origins by default
CORS(app)

# Simulate sending a command to EyeLink by logging it
@app.route('/send_command', methods=['POST', 'OPTIONS'])  # Handle both POST and OPTIONS requests
def send_command():
    if request.method == 'OPTIONS':
        # This is the preflight request, we return a 200 OK with CORS headers
        return jsonify({'status': 'success'}), 200

    data = request.json
    command = data.get('command')
    if command:
        # Simulate sending the command by printing it
        print(f"Simulated sending command to EyeLink: {command}")
        return jsonify({'status': 'success', 'message': f'Command "{command}" simulated as sent to EyeLink'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'No command provided'}), 400

if __name__ == '__main__':
    # Run the server on localhost and port 5000
    app.run(host='0.0.0.0', port=5000)
