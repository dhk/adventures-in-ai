from flask import Flask, jsonify
from flask_cors import CORS, cross_origin

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

# Basic route returning JSON
@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({
        'message': 'Hello from Flask!',
        'status': 'success'
    })

# Route with specific CORS settings
@app.route('/api/restricted', methods=['GET', 'POST'])
@cross_origin(
    origins=['http://localhost:3000', 'https://yourdomain.com'],
    methods=['GET', 'POST'],
    allow_headers=['Content-Type']
)
def restricted():
    return jsonify({
        'message': 'This is a restricted endpoint',
        'status': 'success'
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)

# Requirements (save as requirements.txt):
# flask==3.0.0
# flask-cors==4.0.0