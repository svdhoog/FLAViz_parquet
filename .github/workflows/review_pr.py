import os
import sys
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
        "security vulnerabilities, or departures from clean coding standards. "
        "Keep your feedback highly technical, specific, and actionable.\n\n"
        f"```diff\n{pr_diff}\n```"
    )

    # By passing 'openrouter/auto', OpenRouter dynamically decides which model
    # (e.g., Claude, GPT, Gemini) is best suited to parse and review the diff.
    response = client.chat.completions.create(
        model="openrouter/auto",
        messages=[{"role": "user", "content": prompt}]
    )

    review_output = response.choices[0].message.content
    print(review_output)

if __name__ == "__main__":
    main()
