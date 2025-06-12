import os
import subprocess
import json
import requests
from bs4 import BeautifulSoup

# 🧠 Summarize with Gemini
def summarize_with_gemini(changes):
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{
                "text": f"Summarize these selector changes for the QA team:\n{changes}"
            }]
        }]
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    else:
        print("Gemini API Error:", response.status_code, response.text)
        return "Summary generation failed."

# 🔍 Extract selectors
def extract_selectors(content):
    soup = BeautifulSoup(content, 'html.parser')
    selectors = set()
    for tag in soup.find_all(True):
        if 'class' in tag.attrs:
            selectors.update(f".{cls}" for cls in tag['class'])
        if 'id' in tag.attrs:
            selectors.add(f"#{tag['id']}")
    return selectors

# 📁 Git diff and selector comparison
def main():
    result = subprocess.run(['git', 'diff', '--name-only', 'HEAD^'], capture_output=True, text=True)
    changed_files = [f for f in result.stdout.splitlines() if f.endswith(('.html', '.css', '.js', '.jsx'))]

    all_changes = {}
    raw_summary = ""

    for file in changed_files:
        old_ver = subprocess.run(['git', 'show', f'HEAD^:{file}'], capture_output=True, text=True).stdout
        new_ver = subprocess.run(['git', 'show', f'HEAD:{file}'], capture_output=True, text=True).stdout

        old_selectors = extract_selectors(old_ver)
        new_selectors = extract_selectors(new_ver)

        added = new_selectors - old_selectors
        removed = old_selectors - new_selectors

        if added or removed:
            all_changes[file] = {"added": list(added), "removed": list(removed)}

            raw_summary += f"\n📄 {file}\n"
            if added:
                raw_summary += "🟢 Added:\n" + "\n".join(f"  {s}" for s in added) + "\n"
            if removed:
                raw_summary += "🔴 Removed:\n" + "\n".join(f"  {s}" for s in removed) + "\n"

    if not raw_summary:
        print("✅ No selector changes found.")
        return

    print("📊 Raw Selector Changes:\n", raw_summary)

    summary = summarize_with_gemini(raw_summary)
    print("\n🧠 Gemini Summary:\n", summary)

    # Optional: Save to file
    with open("selector_changes.json", "w") as f:
        json.dump(all_changes, f, indent=2)

if __name__ == "__main__":
    main()
