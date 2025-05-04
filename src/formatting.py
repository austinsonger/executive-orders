import re

def format_content(content):
    """Format the executive order content with proper markdown styling"""
    if not content:
        return ""
    # Clean up the content first
    formatted = content.strip()

    # Format the preamble section
    preamble_pattern = r'Title 3—\s*The President\s*Executive Order (\d+) of ([^\n]+)\n([^\n]+)\s*By the authority'
    preamble_replacement = r'''## Preamble

**Title 3—The President**
**Executive Order \1 of \2**
**\3**

By the authority'''

    formatted = re.sub(preamble_pattern, preamble_replacement, formatted)

    # Clean up the authority section spacing and format
    formatted = re.sub(r'By the authority([^:]+):', r'''### Authority

By the authority\1:''', formatted)

    # Create list of common section titles to bold
    title_words = [
        "Purpose", "Policy", "Reinstatement of Prior Administration Policy",
        "Amendments to Prior Administration Policy", "Conforming Regulatory Changes",
        "Reg", "Additional Positions for Consideration", "Revocation",
        "General Provisions", "Implementation", "Enforcement", "Definitions",
        "Scope", "Authority", "Effective Date", "Amendments", "Review",
        "Compliance", "Administration", "Oversight"
    ]

    # Format main section headers with bold titles on new line
    def bold_section_title(match):
        section_num = match.group(1)
        title = match.group(2).strip()

        # Check if any of the title words appear in the section title
        for word in title_words:
            if word.lower() in title.lower():
                # Find the original word case
                original_word_match = re.search(rf'{re.escape(word)}', title, re.IGNORECASE)
                if original_word_match:
                    original_word = original_word_match.group(0)
                    # Remove the word from the section header and put it bold on next line
                    title = title.replace(original_word, "").strip()
                    # Ensure title isn't empty after removal
                    title_part = f" {title}" if title else ""
                    return f"### Section {section_num}.{title_part}\n\n**{original_word}**\n"

        # If no special word found, just return the normal header
        return f"### Section {section_num}. {title}"

    # Apply section header formatting
    formatted = re.sub(r'(?m)^(?:Sec\.|Section)\s*(\d+)\s*\.\s*([^\.]+)\.?', bold_section_title, formatted)

    # Fix the custom title pattern to avoid look-behind issues and handle potential colons
    custom_title_pattern = r'(\n### Section \d+\.(?:[^\n]*)\n\n\*\*[^\n]+\*\*\n)([A-Za-z ]+):'
    formatted = re.sub(custom_title_pattern, r'\1**\2**\n', formatted)


    # Add proper spacing between paragraphs (more robust approach)
    # Split into lines, process, then rejoin
    lines = formatted.split('\n')
    processed_lines = []
    for i, line in enumerate(lines):
        processed_lines.append(line)
        # Add double newline after sentences ending with punctuation, followed by a capital letter or section marker
        if re.match(r'.*[.!?]$', line) and i + 1 < len(lines) and (re.match(r'^[A-Z(]', lines[i+1]) or re.match(r'^###', lines[i+1])):
             if not lines[i+1].strip().startswith('('): # Avoid extra space before list items
                 processed_lines.append('') # Add an empty line for spacing

    formatted = '\n'.join(processed_lines)


    # Format subsections with letters and ensure proper spacing
    formatted = re.sub(r'\n\s*\(([a-z])\)\s*', r'\n\n(\1) ', formatted)

    # Format roman numeral subsections with proper indentation
    formatted = re.sub(r'\n\s*\(([ivxIVX]+)\)\s*', r'\n    (\1) ', formatted)

    # Format numbered subsections with proper indentation
    formatted = re.sub(r'\n\s*\((\d+)\)\s*', r'\n    (\1) ', formatted)

    # Ensure proper spacing between sections and after headers
    formatted = re.sub(r'\n{3,}', r'\n\n', formatted) # Collapse excess newlines
    formatted = re.sub(r'(### [^\n]+)\n(?!\n)', r'\1\n\n', formatted) # Space after headers

    # Fix any instances where paragraph breaks were added incorrectly within list items
    formatted = re.sub(r'(\n\s+\([a-z\dIVX]+\)\s+.*?)\n\n', r'\1\n', formatted)

    # Clean up any remaining whitespace issues
    formatted = re.sub(r'(?m)^\s+$', '', formatted) # Remove lines with only whitespace
    formatted = formatted.strip() # Remove leading/trailing whitespace

    return formatted