#!/usr/bin/env python3
"""
Test script to demonstrate filename sanitization for audiobook generation.
Shows how problematic characters are handled to prevent validation errors.
"""

def sanitize_filename(text):
    # Remove or replace problematic characters that can cause issues with file systems and security validation
    text = text.replace("'", '').replace('"', '').replace('/', ' ').replace('.', ' ')
    text = text.replace(':', '').replace('?', '').replace('\\', '').replace('|', '')
    text = text.replace('*', '').replace('<', '').replace('>', '').replace('&', 'and')
    text = text.replace(',', '').replace(';', '').replace('!', '').replace('@', '')
    text = text.replace('#', '').replace('$', '').replace('%', '').replace('^', '')
    text = text.replace('(', '').replace(')', '').replace('[', '').replace(']', '')
    text = text.replace('{', '').replace('}', '').replace('=', '').replace('+', '')
    
    # Normalize whitespace and trim
    text = ' '.join(text.split())
    
    return text

def test_filename_sanitization():
    """Test various problematic chapter titles."""
    
    test_cases = [
        "Chapter 2 Dont Get Carried Away, Said God",
        "Chapter 1: The Beginning!",
        "Part 3 - What's Next?",
        "Section A (Important Notes)",
        "Chapter 5: Money & Power",
        "Epilogue: The End... Or Is It?",
        "Chapter 10 - 50% Done!",
        "Intro: Hello, World! #1",
    ]
    
    print("Filename Sanitization Test")
    print("=" * 60)
    
    for original in test_cases:
        sanitized = sanitize_filename(original)
        filename = f"{sanitized}.wav"
        
        print(f"Original:  '{original}'")
        print(f"Sanitized: '{sanitized}'")
        print(f"Filename:  '{filename}'")
        print("-" * 40)
    
    # Test the specific problematic case from the error
    problematic = "Chapter 2 Dont Get Carried Away, Said God"
    sanitized_problematic = sanitize_filename(problematic)
    
    print("\nSpecific Error Case:")
    print(f"Original problematic: '{problematic}'")
    print(f"Sanitized result:     '{sanitized_problematic}'")
    print(f"Final filename:       '{sanitized_problematic}.wav'")
    
    # Show character removal
    removed_chars = set(problematic) - set(sanitized_problematic + ' ')
    if removed_chars:
        print(f"Removed characters:   {sorted(removed_chars)}")
    else:
        print("No characters removed (only whitespace normalized)")

if __name__ == "__main__":
    test_filename_sanitization()