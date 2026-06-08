import re

with open("aizen/tools.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update tools array
tools_replacement = '''
    {
        "type": "function",
        "function": {
            "name": "replace_file_content",
            "description": "Edits a single contiguous block of an existing file. Uses start_line and end_line bounds to locate the target_content reliably.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file to edit.",
                    },
                    "target_content": {
                        "type": "string",
                        "description": "The exact existing text block to replace.",
                    },
                    "replacement_content": {
                        "type": "string",
                        "description": "The replacement text.",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Starting line number (1-indexed) to search within.",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Ending line number (1-indexed) to search within.",
                    },
                    "allow_multiple": {
                        "type": "boolean",
                        "description": "If true, replaces all occurrences within the bounds.",
                    }
                },
                "required": ["filepath", "target_content", "replacement_content", "start_line", "end_line"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "multi_replace_file_content",
            "description": "Edits multiple non-adjacent blocks of an existing file in a single pass.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file to edit.",
                    },
                    "replacement_chunks": {
                        "type": "array",
                        "description": "List of chunks to replace.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "target_content": { "type": "string" },
                                "replacement_content": { "type": "string" },
                                "start_line": { "type": "integer" },
                                "end_line": { "type": "integer" },
                                "allow_multiple": { "type": "boolean" }
                            },
                            "required": ["target_content", "replacement_content", "start_line", "end_line"]
                        }
                    }
                },
                "required": ["filepath", "replacement_chunks"],
            },
        },
    },
'''

# Find edit_file dictionary and replace it (careful with regex)
pattern = re.compile(r'\{\s*"type":\s*"function",\s*"function":\s*\{\s*"name":\s*"edit_file".*?\}\s*\},', re.DOTALL)
content = pattern.sub(tools_replacement, content)

# Update write_file schema to add start_line and end_line
write_file_props = r'"properties":\s*\{\s*"filepath":\s*\{.*?\},\s*"content":\s*\{.*?\}(?=\s*\})'
new_write_file_props = '''"properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file to create/overwrite."
                    },
                    "content": {
                        "type": "string",
                        "description": "The full content to write."
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Optional starting line for absolute block rewrite."
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Optional ending line for absolute block rewrite."
                    }'''
content = re.sub(write_file_props, new_write_file_props, content, flags=re.DOTALL)

with open("aizen/tools.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Patch 1 done")
