#!/usr/bin/env python3
"""
Debug the message splitting algorithm
"""

def debug_split_message(text: str, max_message_length: int = 100) -> list:
    """Debug version of message splitting"""
    if len(text) <= max_message_length:
        return [text]
    
    parts = []
    remaining = text
    
    # Reserve space for part indicators like " (1/N)"
    part_indicator_space = 8  # " (XX/XX)" takes up to 8 characters
    effective_limit = max_message_length - part_indicator_space
    
    print(f"Original text: '{text}'")
    print(f"Length: {len(text)}, Max: {max_message_length}, Effective: {effective_limit}")
    
    # First pass: split text into parts without indicators
    temp_parts = []
    while remaining:
        print(f"\nRemaining: '{remaining}' ({len(remaining)} chars)")
        
        if len(remaining) <= effective_limit:
            temp_parts.append(remaining)
            print(f"Final part: '{remaining}'")
            break
        
        # Find the best place to split (prefer word boundaries)
        split_point = effective_limit
        
        # Look for word boundary within last 50 characters
        word_boundary_start = max(0, effective_limit - 50)
        last_space = remaining.rfind(' ', word_boundary_start, effective_limit)
        
        print(f"Looking for space between {word_boundary_start} and {effective_limit}")
        print(f"Found space at position: {last_space}")
        
        if last_space > word_boundary_start:
            split_point = last_space
            print(f"Using word boundary at {split_point}")
        else:
            print(f"No good word boundary, splitting at {split_point}")
        
        # Split the message
        part = remaining[:split_point]
        temp_parts.append(part)
        print(f"Part: '{part}'")
        
        remaining = remaining[split_point:]
        print(f"After split: '{remaining}'")
        
        # Only remove leading space if we split at a space boundary
        if remaining.startswith(' '):
            remaining = remaining[1:]
            print(f"Removed leading space: '{remaining}'")
    
    return temp_parts

# Test case
test_text = "This is a longer message that should be split into multiple parts because it exceeds the configured maximum message length limit."
parts = debug_split_message(test_text)

print(f"\nFinal parts:")
for i, part in enumerate(parts, 1):
    print(f"  {i}: '{part}' ({len(part)} chars)")

# Reconstruct
reconstructed = ''.join(parts)
print(f"\nOriginal:      '{test_text}'")
print(f"Reconstructed: '{reconstructed}'")
print(f"Match: {test_text == reconstructed}")