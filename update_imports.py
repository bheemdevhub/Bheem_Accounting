import os

# Directory to scan
BASE_DIR = "./app"

# Old to new import mappings
replacements = {
    "from app.core.": "from bheem_core.",
    "from app.shared.": "from bheem_core.shared.",
    "import app.core.": "import bheem_core.",
    "import app.shared.": "import bheem_core.shared.",
    "from ...core.": "from bheem_core.",
    "from ...shared.": "from bheem_core.shared.",
    "from ..core.": "from bheem_core.",
    "from ..shared.": "from bheem_core.shared.",
}

# File extensions to check
PYTHON_EXT = ".py"

def update_imports():
    for root, _, files in os.walk(BASE_DIR):
        for filename in files:
            if filename.endswith(PYTHON_EXT):
                filepath = os.path.join(root, filename)

                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                original = content

                for old, new in replacements.items():
                    content = content.replace(old, new)

                if content != original:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"✅ Updated: {filepath}")

if __name__ == "__main__":
    update_imports()
    print("🎉 Done! All 'app.core' and 'app.shared' imports updated to 'bheem_core'.")
