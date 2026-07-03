import os, re

base = "C:/workspace/agentDevBible"

# Find all .md files and fix ">" that appears before chapter numbers in headers
for fname in os.listdir(base):
    if not fname.endswith(".md"):
        continue
    fpath = os.path.join(base, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Fix headers like "## >13.1" -> "## 13.1"
    content = re.sub(r'^(#{2,4})\s+>', r'\1 ', content, flags=re.MULTILINE)
    
    if content != original:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed > in headers: {fname}")

print("Done.")
