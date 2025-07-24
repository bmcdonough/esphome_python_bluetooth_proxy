#!/usr/bin/env python3
"""Fix linting issues automatically."""

import re
import os
from pathlib import Path

def fix_file(filepath):
    """Fix linting issues in a single file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Remove unused imports (common patterns)
    unused_imports = [
        r'from typing import.*?Any.*?\n',
        r'from typing import.*?Callable.*?\n', 
        r'from typing import.*?Union.*?\n',
        r'from typing import.*?Optional.*?\n(?!.*Optional)',
        r'import time\n(?!.*time\.)',
        r'import struct\n(?!.*struct\.)',
        r'from bleak\.backends\.device import BLEDevice\n(?!.*BLEDevice)',
        r'from bleak\.backends\.service import BleakGATTService\n(?!.*BleakGATTService)',
        r'from bleak\.backends\.descriptor import BleakGATTDescriptor\n(?!.*BleakGATTDescriptor)',
    ]
    
    for pattern in unused_imports:
        content = re.sub(pattern, '', content, flags=re.MULTILINE)
    
    # Fix type annotations
    content = re.sub(r"proxy: 'BluetoothProxy'", "proxy", content)
    content = re.sub(r"bluetooth_proxy: 'BluetoothProxy'", "bluetooth_proxy", content)
    
    # Fix bare except
    content = re.sub(r'except:', 'except Exception:', content)
    
    # Fix long lines by breaking them
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        if len(line) > 88 and 'logger.' in line:
            # Break long logger lines
            if 'f"' in line:
                # Find the f-string and break it
                match = re.search(r'logger\.\w+\(f"([^"]+)"\)', line)
                if match:
                    indent = len(line) - len(line.lstrip())
                    prefix = line[:line.find('logger')]
                    log_level = re.search(r'logger\.(\w+)', line).group(1)
                    msg = match.group(1)
                    
                    if len(msg) > 60:
                        # Break the message
                        words = msg.split()
                        line1_words = []
                        line2_words = []
                        current_len = 0
                        
                        for word in words:
                            if current_len + len(word) < 50:
                                line1_words.append(word)
                                current_len += len(word) + 1
                            else:
                                line2_words.append(word)
                        
                        if line2_words:
                            line1 = f'{prefix}logger.{log_level}('
                            line2 = f'{" " * (indent + 4)}f"{" ".join(line1_words)} "'
                            line3 = f'{" " * (indent + 4)}f"{" ".join(line2_words)}")'
                            fixed_lines.extend([line1, line2, line3])
                            continue
        
        fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    # Clean up multiple empty lines
    content = re.sub(r'\n\n\n+', '\n\n', content)
    
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Fixed {filepath}")
    
def main():
    """Fix all Python files."""
    src_dir = Path("src/esphome_bluetooth_proxy")
    
    for py_file in src_dir.glob("*.py"):
        fix_file(py_file)
    
    # Fix test files
    for test_file in Path(".").glob("test_*.py"):
        fix_file(test_file)

if __name__ == "__main__":
    main()
