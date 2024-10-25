from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)
#CORS(app)  # This enables CORS for all routes
CORS(app, resources={r"/*": {"origins": "*"}})


@app.route('/schedule', methods=['POST', 'OPTIONS'])
def schedule_post():
    print("here")
    if request.method == 'OPTIONS':
        print("here")
        print(request)
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')  # Add this line
        return response


    # Actual POST request handling
    data = request.json
    post_time = data.get('datetime')
    message = data.get('message')

    # Convert datetime to Python datetime object
    post_time = datetime.strptime(post_time, "%Y-%m-%dT%H:%M")

    # ... [rest of your scheduling logic] ...

    return jsonify({"status": "Post scheduled successfully"}), 200

# ... [rest of your code] ...

if __name__ == '__main__':
    print ('hello world')
    app.run(debug=True)