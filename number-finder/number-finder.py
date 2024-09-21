from flask import Flask, request, render_template
from mpmath import mp

# Initialize the Flask app
app = Flask(__name__)

# Set precision for pi (up to 1 million decimal places)
mp.dps = 1000000  # Adjust as needed
pi_str = str(mp.pi)[2:]  # Get pi's decimal places as a string (skip '3.')

# Define a function to find the input string in pi
def find_in_pi(number_str):
    position = pi_str.find(number_str)
    if position == -1:
        return f"The sequence {number_str} is not found within the first {len(pi_str)} decimal places of pi."
    else:
        return f"The sequence {number_str} first appears at position {position + 1} in the decimal places of pi."

# Define the home route to display the form and handle the user input
@app.route('/', methods=['GET', 'POST'])
def index():
    result = ""
    if request.method == 'POST':
        number_str = request.form['number_str']
        if len(number_str) > 9 or not number_str.isdigit():
            result = "Please enter a valid string of digits (up to 9 digits)."
        else:
            result = find_in_pi(number_str)
    return render_template('index.html', result=result)

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
