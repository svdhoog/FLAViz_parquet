import os
import sys
import json
from openai import OpenAI

def main():
    # Fetch the code diff passed from the GitHub workflow environment
    pr_diff = os.getenv("PR_DIFF")
    if not pr_diff:
        print("No PR diff provided.")
        sys.exit(0)

    # Initialize the client pointing to OpenRouter
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY")
    )

    prompt = (
        "You are an expert senior software engineer performing a code review. "
        "Analyze the following git diff. Identify bugs, performance bottlenecks, "
        "security vulnerabilities, or departures from clean coding standards.\n\n"
        "Format your entire response strictly as a valid JSON object containing an array of issues. "
        "Do not include markdown blocks like ```json or any conversational text. "
        "Use this exact schema:\n"
        "{\n"
        '  "issues": [\n'
        "    {\n"
        '      "title": "Short descriptive title of the problem",\n'
        '      "body": "Detailed technical explanation, context, and actionable fix or suggestion."\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"```diff\n{pr_diff}\n```"
    )

    # Utilizing the free Llama 3.3 70B model which features strong instruction following
    response = client.chat.completions.create(
        model="meta-llama/llama-3.3-70b-instruct:free",
        messages=[{"role": "user", "content": prompt}]
    )

    review_output = response.choices[0].message.content.strip()
    
    # Strip markdown block wrappers if the model accidentally returns them despite instructions
    if review_output.startswith("```"):
        review_output = review_output.strip("`").replace("json", "", 1).strip()

    print(review_output)

if __name__ == "__main__":
    main()