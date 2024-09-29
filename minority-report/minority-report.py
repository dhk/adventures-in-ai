from flask import Flask, render_template, request
from openai import OpenAI

client = OpenAI(api_key='YOUR_OPENAI_API_KEY')
import anthropic  # Assuming Claude's API client is available

app = Flask(__name__)

# Set up API keys for OpenAI and Claude
claude_client = anthropic.Client(api_key='YOUR_CLAUDE_API_KEY')
# For Gemini, you would add a similar setup

# Define functions to query each API
def get_chatgpt_response(question):
    response = client.completions.create(model="gpt-4",
    prompt=question,
    max_tokens=100)
    return response.choices[0].text

def get_claude_response(question):
    response = claude_client.completion(
        prompt=question,
        max_tokens_to_sample=100
    )
    return response.completion

# This is a placeholder for the Gemini API function
def get_gemini_response(question):
    return "Gemini response placeholder"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        company_name = request.form['company']
        questions = request.form.getlist('questions')

        # Collect answers
        chatgpt_answers = [get_chatgpt_response(q) for q in questions]
        claude_answers = [get_claude_response(q) for q in questions]
        gemini_answers = [get_gemini_response(q) for q in questions]

        # Build markdown table and compare answers
        comparison_results = compare_answers(questions, chatgpt_answers, claude_answers, gemini_answers)
        return render_template('results.html', markdown_table=comparison_results)

    return render_template('index.html')

def compare_answers(questions, chatgpt, claude, gemini):
    markdown_table = "| Question | ChatGPT | Claude | Gemini | Similarity/Outlier |\n"
    markdown_table += "|---|---|---|---|---|\n"

    for i, question in enumerate(questions):
        similarity_status = check_similarity(chatgpt[i], claude[i], gemini[i])
        markdown_table += f"| {question} | {chatgpt[i]} | {claude[i]} | {gemini[i]} | {similarity_status} |\n"

    return markdown_table

def check_similarity(answer1, answer2, answer3):
    # Basic similarity check (can be expanded to use NLP techniques)
    if answer1 == answer2 == answer3:
        return "similar"
    else:
        return "outlier"

if __name__ == '__main__':
    app.run(debug=True)
