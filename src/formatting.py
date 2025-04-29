import re

def format_content(content):
    """Format the executive order content with proper markdown styling"""
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
    
    # Add proper spacing between paragraphs
    sentences = formatted.split('. ')
    formatted = '. '.join(sentences)
    formatted = re.sub(r'(?<=[.!?])\s+(?=[A-Z])', r'\n\n', formatted)
    
    # Ensure proper spacing between sections
    formatted = re.sub(r'\n{3,}', r'\n\n', formatted)
    formatted = re.sub(r'(### [^\n]+)\n(?!\n)', r'\1\n\n', formatted)
    
    # Clean up any remaining whitespace issues
    formatted = re.sub(r'(?m)^\s+$', '', formatted)
    
    return formatted

def bold_section_title(match):
    """Helper function to bold section titles"""
    section_num = match.group(1)
    title = match.group(2).strip()
    
    # Check if any of the title words appear in the section title
    for word in title_words:
        if word.lower() in title.lower():
            # Replace the word with its bold version, maintaining original case
            original_word = re.search(rf'{word}', title, re.IGNORECASE).group(0)
            # Remove the word from the section header and put it bold on next line
            title = title.replace(original_word, "").strip()
            return f"### Section {section_num}.\n\n**{original_word}**\n"
    
    # If no special word found, just return the normal header
    return f"### Section {section_num}. {title}"