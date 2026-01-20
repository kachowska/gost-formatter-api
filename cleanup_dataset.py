#!/usr/bin/env python3
"""
Final cleanup for VAK RB bibliography dataset.
Fixes remaining punctuation issues.
"""

import json
import re


def load_dataset(filepath: str) -> dict:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_dataset(data: dict, filepath: str):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clean_text(text: str) -> str:
    """Apply all cleanup rules to text."""

    # Protect dissertation ellipsis with placeholder
    ELLIPSIS_PLACEHOLDER = "<<<ELLIPSIS>>>"
    text = text.replace(". ... ", f". {ELLIPSIS_PLACEHOLDER} ")

    # 1. Fix double periods (journal names etc.)
    text = re.sub(r'журн\.\.', 'журн.', text)
    text = re.sub(r'([а-яё])\.\.([^.])', r'\1.\2', text)

    # 2. Fix double spaces
    text = re.sub(r'  +', ' ', text)

    # 3. Fix ". –X" -> ". – X" (space after dash, except for digits/ranges)
    text = re.sub(r'\. –([А-ЯЁа-яёA-Za-z])', r'. – \1', text)

    # 4. Fix ":X" -> ": X" (but not in URLs like http://)
    text = re.sub(r':([А-ЯЁа-яёA-Za-z])', r': \1', text)

    # 5. Ensure no spaces around dash in numeric ranges
    text = re.sub(r'(\d) – (\d)', r'\1–\2', text)
    text = re.sub(r'(\d)– (\d)', r'\1–\2', text)
    text = re.sub(r'(\d) –(\d)', r'\1–\2', text)

    # 6. Fix page ranges "С. X – Y" -> "С. X–Y"
    text = re.sub(r'С\. (\d+) ?– ?(\d+)', r'С. \1–\2', text)

    # 7. Fix missing space after initials before surname
    text = re.sub(r'(\w\. \w\.)([А-ЯЁA-Z])', r'\1 \2', text)

    # 8. Fix "№X" -> "№ X"
    text = re.sub(r'№([А-ЯЁа-яёA-Za-z0-9])', r'№ \1', text)

    # 9. Fix "Т.X" -> "Т. X" and "Вып.X" -> "Вып. X"
    text = re.sub(r'Т\.(\d)', r'Т. \1', text)
    text = re.sub(r'Вып\.(\d)', r'Вып. \1', text)
    text = re.sub(r'кн\.(\d)', r'кн. \1', text)

    # 10. Fix trailing spaces before punctuation
    text = re.sub(r' \.', '.', text)
    text = re.sub(r' ,', ',', text)

    # 11. Ensure proper spacing around " – " separators (not in ranges)
    text = re.sub(r'\. –([^\s\d–])', r'. – \1', text)

    # Restore dissertation ellipsis
    text = text.replace(ELLIPSIS_PLACEHOLDER, "...")

    return text


def main():
    print("Loading dataset...")
    dataset = load_dataset('vak_training.json')

    print(f"Processing {len(dataset['examples'])} examples...")

    cleaned_count = 0
    for ex in dataset['examples']:
        original = ex['example']
        cleaned = clean_text(original)

        if original != cleaned:
            cleaned_count += 1
            ex['example'] = cleaned

    print(f"Cleaned {cleaned_count} examples")

    print("Saving cleaned dataset...")
    save_dataset(dataset, 'vak_training.json')

    print("Done!")


if __name__ == '__main__':
    main()
