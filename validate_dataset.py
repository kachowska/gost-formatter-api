#!/usr/bin/env python3
"""
Validator for VAK RB bibliography dataset.
Checks punctuation rules and formatting consistency.
"""

import json
import re
from typing import List, Tuple


def load_dataset(filepath: str) -> dict:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_punctuation_errors(text: str) -> List[Tuple[str, str]]:
    """Check for common punctuation errors."""
    errors = []

    # 1. Check for ". –X" (no space after dash, excluding ranges)
    # Find all ". –" followed by non-digit
    pattern1 = re.compile(r'\. –([^\s\d])')
    matches = pattern1.findall(text)
    if matches:
        errors.append(("missing_space_after_dash", f"Found '. –X' without space: {matches}"))

    # 2. Check for ":X" (no space after colon)
    # Exclude URLs like http://
    pattern2 = re.compile(r':([^\s/\d])')
    matches = pattern2.findall(text)
    if matches:
        errors.append(("missing_space_after_colon", f"Found ':X' without space: {matches}"))

    # 3. Check for "И. О.Слово" (no space after initials)
    pattern3 = re.compile(r'(\w\. \w\.)([А-ЯЁа-яёA-Za-z])')
    matches = pattern3.findall(text)
    if matches:
        errors.append(("missing_space_after_initials", f"Found 'X. X.Word' without space: {matches}"))

    # 4. Check for spaces around dash in ranges (should be no spaces)
    pattern4 = re.compile(r'(\d) – (\d)')
    matches = pattern4.findall(text)
    if matches:
        errors.append(("spaces_in_range", f"Found spaces around dash in range: {matches}"))

    pattern4b = re.compile(r'(\d)– (\d)')
    matches = pattern4b.findall(text)
    if matches:
        errors.append(("trailing_space_in_range", f"Found trailing space in range: {matches}"))

    pattern4c = re.compile(r'(\d) –(\d)')
    matches = pattern4c.findall(text)
    if matches:
        errors.append(("leading_space_in_range", f"Found leading space in range: {matches}"))

    # 5. Check for double spaces
    pattern5 = re.compile(r'  +')
    matches = pattern5.findall(text)
    if matches:
        errors.append(("double_spaces", f"Found double spaces: {len(matches)} occurrences"))

    # 6. Check for hyphen instead of dash in year/page ranges
    # Looking for patterns like "2015-2020" (year ranges)
    # But NOT standard numbers like "ГОСТ 7.22-2003" or "ТКП 7696-2024"
    # Only flag if both numbers are plausible years (2000-2030) and first < second
    pattern6 = re.compile(r'(\d{4})-(\d{4})')
    for match in pattern6.finditer(text):
        year1, year2 = int(match.group(1)), int(match.group(2))
        # Only flag as error if both look like years and first < second (actual range)
        if 1990 <= year1 < year2 <= 2030:
            errors.append(("hyphen_instead_of_dash", f"Found hyphen in year range: {match.group(0)}"))

    # Check page ranges with hyphen
    pattern6b = re.compile(r'С\. (\d+)-(\d+)')
    matches = pattern6b.findall(text)
    if matches:
        errors.append(("hyphen_in_page_range", f"Found hyphen in page range (should be dash): {matches}"))

    # 7. Check for "С. X– Y" or "С. X –Y" patterns
    pattern7 = re.compile(r'С\. (\d+) ?– ?(\d+)')
    for match in re.finditer(pattern7, text):
        full_match = match.group(0)
        if ' – ' in full_match or '– ' in full_match or ' –' in full_match:
            errors.append(("page_range_spaces", f"Found spaces in page range: {full_match}"))

    return errors


def validate_json_structure(data: dict) -> List[str]:
    """Validate JSON structure."""
    errors = []

    required_fields = ['description', 'total_examples', 'examples']
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    if 'examples' in data:
        for i, ex in enumerate(data['examples']):
            if 'type' not in ex:
                errors.append(f"Example {i}: missing 'type' field")
            if 'example' not in ex:
                errors.append(f"Example {i}: missing 'example' field")

    return errors


def main():
    dataset = load_dataset('vak_training.json')

    print("=" * 60)
    print("VAK RB Dataset Validation Report")
    print("=" * 60)

    # Structure validation
    structure_errors = validate_json_structure(dataset)
    if structure_errors:
        print(f"\n❌ Structure errors: {len(structure_errors)}")
        for err in structure_errors[:10]:
            print(f"   - {err}")
    else:
        print("\n✅ JSON structure is valid")

    # Punctuation validation
    print(f"\nTotal examples: {len(dataset['examples'])}")

    error_counts = {}
    examples_with_errors = []

    for i, ex in enumerate(dataset['examples']):
        text = ex.get('example', '')
        errors = check_punctuation_errors(text)

        if errors:
            examples_with_errors.append((i, ex['type'], errors))
            for err_type, _ in errors:
                error_counts[err_type] = error_counts.get(err_type, 0) + 1

    if error_counts:
        print(f"\n⚠️  Punctuation issues found:")
        for err_type, count in sorted(error_counts.items(), key=lambda x: -x[1]):
            print(f"   - {err_type}: {count} occurrences")

        print(f"\n📋 Examples with issues ({len(examples_with_errors)} total):")
        for idx, ex_type, errors in examples_with_errors[:10]:
            print(f"   [{idx}] {ex_type}: {errors[0][0]}")
    else:
        print("\n✅ No punctuation errors found!")

    # Sample output
    print("\n" + "=" * 60)
    print("Sample entries by type:")
    print("=" * 60)

    shown_types = set()
    for ex in dataset['examples']:
        if ex['type'] not in shown_types and len(shown_types) < 5:
            shown_types.add(ex['type'])
            print(f"\n[{ex['type']}]")
            print(f"  {ex['example'][:150]}...")

    print("\n" + "=" * 60)
    print("Validation complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
