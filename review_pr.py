import os
import sys
import json
import time
from openai import OpenAI, RateLimitError

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

    max_retries = 3
    review_output = ""
    
    for attempt in range(max_retries):
        try:
            # Switching to the active free Codestral model by Mistral
            response = client.chat.completions.create(
                model="mistralai/codestral-2501:free",
                messages=[{"role": "user", "content": prompt}]
            )
            review_output = response.choices[0].message.content.strip()
            break
        except RateLimitError as e:
            if attempt < max_retries - 1:
                time.sleep(32)
            else:
                raise e

    # Clean up markdown code block indicators if returned by the model
    if review_output.startswith("```"):
        # Split lines and remove the markdown block syntax wrappers cleanly
        lines = review_output.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        review_output = "\n".join(lines).strip()

    print(review_output)

if __name__ == "__main__":
    main()