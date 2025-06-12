import os
import subprocess
import json
import requests
from bs4 import BeautifulSoup

# Optional: summarize changes with AI
def summarize_with_ai(changes):
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Summarize selector changes for QA team."},
            {"role": "user", "content": changes}
        ]
    )
    return response['choices'][0]['message']['content']

# Extract selectors from HTML or JSX
def extract_selectors_from_html(content):
    soup = BeautifulSoup(content, 'html.parser')
    selectors = set()
    for tag in soup.find_all(True):
        if 'class' in tag.attrs:
            for cls in tag['class']:
                selectors.add(f".{cls}")
        if 'id' in tag.attrs:
            selectors.add(f"#{tag['id']}")
    return selectors

# Get changed files in this commit
def get_changed_files():
    result = subprocess.run(['git', 'diff', '--name-only', 'HEAD^'], capture_output=True, text=True)
    return [line.strip() for line in result.stdout.splitlines() if line.endswith(('.html', '.css', '.js', '.jsx'))]

# Get file content from Git history
def get_file_version(commit, filepath):
    try:
        output = subprocess.run(['git', 'show', f'{commit}:{filepath}'], capture_output=True, text=True)
        return output.stdout
    except:
        return ""

# OPTIONAL: Push result to ObservePoint
def update_observepoint(selector_data):
    api_key = os.getenv("OBSERVEPOINT_API_KEY")
    if not api_key:
        print("No ObservePoint API key. Skipping upload.")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    for file, changes in selector_data.items():
        data = {
            "file": file,
            "added_selectors": list(changes['added']),
            "removed_selectors": list(changes['removed']),
        }

        response = requests.post("https://api.observepoint.com/v2/audits/1234/selectors", json=data, headers=headers)
        print("ObservePoint response:", response.status_code)

# Main logic
def main():
    files = get_changed_files()
    if not files:
        print("No relevant files changed.")
        return

    all_changes = {}
    raw_summary = ""

    for file in files:
        old_content = get_file_version('HEAD^', file)
        new_content = get_file_version('HEAD', file)

        old_selectors = extract_selectors_from_html(old_content)
        new_selectors = extract_selectors_from_html(new_content)

        added = new_selectors - old_selectors
        removed = old_selectors - new_selectors

        if added or removed:
            all_changes[file] = {"added": added, "removed": removed}

            raw_summary += f"\n📄 {file}\n"
            if added:
                raw_summary += "🟢 Added:\n" + "\n".join(f"  {s}" for s in added) + "\n"
            if removed:
                raw_summary += "🔴 Removed:\n" + "\n".join(f"  {s}" for s in removed) + "\n"

    if not all_changes:
        print("✅ No selector-level changes found.")
        return

    print(raw_summary)

    if os.getenv("OPENAI_API_KEY"):
        summary = summarize_with_ai(raw_summary)
        print("\n🧠 AI Summary:\n", summary)

    update_observepoint(all_changes)

    with open("selector_changes.json", "w") as f:
        json.dump(all_changes, f, indent=2)

if __name__ == "__main__":
    main()
