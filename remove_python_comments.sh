#!/bin/bash

# Script to remove all Python comments from a git repository
# Detects git root automatically and processes all .py files

set -e

# Function to detect git repository root
find_git_root() {
    local current_dir="$(pwd)"
    
    while [[ "$current_dir" != "/" ]]; do
        if [[ -d "$current_dir/.git" ]]; then
            echo "$current_dir"
            return 0
        fi
        current_dir="$(dirname "$current_dir")"
    done
    
    echo "Error: Not inside a git repository" >&2
    return 1
}

# Function to remove comments from a Python file
remove_python_comments() {
    local file="$1"
    local temp_file=$(mktemp)
    
    # Use sed to remove Python comments while preserving strings
    # This handles:
    # - Lines that start with # (full line comments)
    # - Inline comments (# after code)
    # - Preserves # inside strings (basic protection)
    python3 -c "
import re
import sys

def remove_comments(content):
    lines = content.split('\n')
    result = []
    in_multiline_string = False
    string_delimiter = None
    
    for line in lines:
        new_line = ''
        i = 0
        while i < len(line):
            char = line[i]
            
            # Handle string literals
            if not in_multiline_string and char in ['\"', \"'\"] and (i == 0 or line[i-1] != '\\\\'):
                if string_delimiter is None:
                    string_delimiter = char
                elif char == string_delimiter:
                    string_delimiter = None
                new_line += char
            # Handle triple quotes
            elif not in_multiline_string and i < len(line) - 2 and line[i:i+3] in ['\"\"\"', \"'''\"] and (i == 0 or line[i-1] != '\\\\'):
                if string_delimiter is None:
                    string_delimiter = line[i:i+3]
                    in_multiline_string = True
                    new_line += line[i:i+3]
                    i += 2
                elif line[i:i+3] == string_delimiter:
                    string_delimiter = None
                    in_multiline_string = False
                    new_line += line[i:i+3]
                    i += 2
                else:
                    new_line += char
            # Handle comments
            elif char == '#' and string_delimiter is None and not in_multiline_string:
                # Remove everything from # to end of line
                new_line = new_line.rstrip()
                break
            else:
                new_line += char
            
            i += 1
        
        result.append(new_line)
    
    return '\n'.join(result)

# Read the file
with open('$file', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove comments
cleaned_content = remove_comments(content)

# Write back to file
with open('$file', 'w', encoding='utf-8') as f:
    f.write(cleaned_content)
"
    
    echo "Processed: $file"
}

# Main execution
main() {
    echo "Detecting git repository root..."
    
    local git_root
    git_root=$(find_git_root)
    
    echo "Git root found: $git_root"
    echo "Removing Python comments from all .py files..."
    
    # Change to git root directory
    cd "$git_root"
    
    # Find all Python files and process them
    local file_count=0
    while IFS= read -r -d '' file; do
        if [[ -f "$file" && -r "$file" && -w "$file" ]]; then
            remove_python_comments "$file"
            ((file_count++))
        else
            echo "Skipping unreadable/unwritable file: $file"
        fi
    done < <(find . -name "*.py" -type f -print0)
    
    echo "Complete! Processed $file_count Python files."
    echo "Note: Please review changes before committing."
}

# Run main function
main "$@"