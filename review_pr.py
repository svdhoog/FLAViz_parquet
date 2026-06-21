import os
import sys
import json
import time
from openai import OpenAI, RateLimitError

def main():
    diff_file_path = "pr_diff.txt"
    if not os.path.exists(diff_file_path):
        print("No PR diff file found at pr_diff.txt.")
        sys.exit(0)
        
    with open(diff_file_path, "r", encoding="utf-8") as f:
        pr_diff = f.read().strip()

    if not pr_diff:
        print("PR diff file is empty.")
        sys.exit(0)

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
            response = client.chat.completions.create(
                model="qwen/qwen-2.5-coder-32b-instruct:free",
                messages=[{"role": "user", "content": prompt}]
            )
            candidate_output = response.choices[0].message.content.strip()
            
            # Clean up markdown formatting blocks if present
            if candidate_output.startswith("```"):
                lines = candidate_output.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                candidate_output = "\n".join(lines).strip()
            
            # Isolate and validate JSON structure internally before approving
            start_idx = candidate_output.find("{")
            end_idx = candidate_output.rfind("}")
            if start_idx != -1 and end_idx != -1:
                json_string = candidate_output[start_idx:end_idx+1]
                json.loads(json_string)  # Structural proof check
                review_output = json_string
                break
            else:
                raise ValueError("JSON braces missing in response output.")
                
        except (RateLimitError, ValueError, json.JSONDecodeError) as e:
            if attempt < max_retries - 1:
                time.sleep(32)
            else:
                # If all retries fail, write raw response string to let the workflow handle the fallback
                review_output = response.choices[0].message.content.strip() if 'response' in locals() else str(e)

    output_file_path = "review_response.json"
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(review_output)

if __name__ == "__main__":
    main()