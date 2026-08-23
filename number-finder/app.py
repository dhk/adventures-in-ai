from flask import Flask, request, render_template
from mpmath import mp
import os  # Import os to handle environment variables

# Initialize the Flask app
app = Flask(__name__)

# Default precision for pi (up to 1 million decimal places)
DEFAULT_DIGITS = 1000000

# Function to generate pi to the specified number of digits
def generate_pi(num_digits):
    mp.dps = num_digits  # Set precision based on user input
    return str(mp.pi)[2:]  # Get pi's decimal places as a string (skip '3.')

# Define a function to find the input string in pi, now receiving formatted_pi_length as argument
def find_in_pi(number_str, pi_str, formatted_pi_length):
    position = pi_str.find(number_str)
    if position == -1:
        return f"The sequence {number_str} is not found within the first {formatted_pi_length} decimal places of Pi."
    else:
        return f"The sequence {number_str} first appears at position {position + 1:,} in the decimal places of Pi."

# Define the home route to display the form and handle user input
@app.route('/', methods=['GET', 'POST'])
def index():
    result = ""
    disclaimer = "Note: We do not store any information. Please do not search for sensitive data like social security numbers."
    num_digits = DEFAULT_DIGITS  # Default value is 1 million digits of pi
    formatted_pi_length = f"{DEFAULT_DIGITS:,}"  # Default formatted value for the first page load

    if request.method == 'POST':
        number_str = request.form['number_str']
        num_digits = int(request.form['num_digits'])
        if len(number_str) > 9 or not number_str.isdigit():
            result = "Please enter a valid string of digits (up to 9 digits)."
        elif num_digits > 1000000001:
            result = "Please enter a number of digits up to or including 1,000,000,001."
        else:
            pi_str = generate_pi(num_digits)
            formatted_pi_length = f"{num_digits:,}"  # Format the number of digits with commas
            result = find_in_pi(number_str, pi_str, formatted_pi_length)

    return render_template('index.html', result=result, disclaimer=disclaimer, formatted_pi_length=formatted_pi_length, num_digits=num_digits)

# Run the app
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Heroku provides PORT environment variable
    app.run(host='0.0.0.0', port=port)
