from openai import OpenAI
import os

from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# this_key = os.getenv("OPENAI_API_KEY") # this is working ok
#print(f""" key is {this_key}""")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Set your OpenAI API key
  # Or you can directly set the key like openai.api_key = "your-api-key"

# Test the API key by making a simple request to get a completion
try:
    # Make a chat completion request using the v1/chat/completions endpoint
    response = client.chat.completions.create(model="gpt-4",  # Or "gpt-3.5-turbo"
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello world"}
    ],
    max_tokens=50)

    # Print the response to verify the key works
    print("API request was successful.")
    print("Response:", response.choices[0].text.strip())
    print ('done')

#except OpenAI.AuthenticationError as e:
#    print("Authentication error: The API key may be incorrect.")
#except OpenAI.OpenAIError as e:
#    print(f"OpenAI error: {e}")
except:
    print ("Oops")