import re
import os

with open("aizen/tools.py", "r", encoding="utf-8") as f:
    content = f.read()

new_funcs = '''
import ast

def _validate_syntax(filepath: str, file_content: str) -> str | None:
    """Return error message if syntax is invalid, else None."""
    if filepath.endswith(".py"):
        try:
            ast.parse(file_content)
        except SyntaxError as e:
            return f"SyntaxError in Python code: {e.msg} at line {e.lineno}, col {e.offset}"
    return None

def _fuzzy_find_block(file_lines: list[str], target_content: str, start_line: int, end_line: int) -> str | None:
    """Find the best match for target_content within the specified line bounds."""
    start_idx = max(0, start_line - 1)
    end_idx = min(len(file_lines), end_line)
    search_lines = file_lines[start_idx:end_idx]
    search_str = "".join(search_lines)
    
    # Try exact match first
    if target_content in search_str:
        return target_content
        
    # Auto-heal whitespace differences
    parts = re.split(r'\\s+', target_content.strip())
    escaped_parts = [re.escape(p) for p in parts if p]
    if escaped_parts:
        pattern_str = r'\\s+'.join(escaped_parts)
        try:
            matches = list(re.finditer(pattern_str, search_str))
            if len(matches) == 1:
                return matches[0].group(0)
        except Exception:
            pass

    # Try difflib sliding window
    target_lines = target_content.splitlines(keepends=True)
    if not target_lines:
        return None
        
    best_ratio = 0
    best_match = None
    window_size = len(target_lines)
    
    for i in range(len(search_lines) - window_size + 1):
        window = "".join(search_lines[i:i + window_size])
        ratio = difflib.SequenceMatcher(None, target_content, window).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = window
            
    if best_ratio > 0.8:
        return best_match
        
    return None

def replace_file_content(filepath: str, target_content: str, replacement_content: str, start_line: int, end_line: int, allow_multiple: bool = False, auto_approve: bool = False) -> str:
    """Edits a single contiguous block of an existing file."""
    return multi_replace_file_content(
        filepath,
        [{"target_content": target_content, "replacement_content": replacement_content, "start_line": start_line, "end_line": end_line, "allow_multiple": allow_multiple}],
        auto_approve
    )

def multi_replace_file_content(filepath: str, replacement_chunks: list[dict], auto_approve: bool = False) -> str:
    """Edits multiple non-adjacent blocks of an existing file."""
    try:
        if not os.path.exists(filepath):
            return f"Error: File '{filepath}' does not exist."

        with open(filepath, encoding="utf-8", errors="ignore") as f:
            file_content = f.read()
            
        file_lines = file_content.splitlines(keepends=True)
        new_file_content = file_content
        
        # Apply chunks sequentially
        for idx, chunk in enumerate(replacement_chunks):
            target = chunk["target_content"]
            replacement = chunk["replacement_content"]
            sl = chunk.get("start_line", 1)
            el = chunk.get("end_line", len(file_lines))
            allow_mult = chunk.get("allow_multiple", False)
            
            actual_old = _fuzzy_find_block(file_lines, target, sl, el)
            if not actual_old:
                return f"Error in chunk {idx+1}: Could not find the specified target_content within lines {sl}-{el}. Please check your exact text."
                
            occurrence_count = new_file_content.count(actual_old)
            if occurrence_count == 0:
                return f"Error in chunk {idx+1}: The text was found in the original file, but is no longer present after preceding replacements."
            if occurrence_count > 1 and not allow_mult:
                return f"Error in chunk {idx+1}: Found {occurrence_count} occurrences of the target text. Provide a more specific block or set allow_multiple=true."
                
            new_file_content = new_file_content.replace(actual_old, replacement, -1 if allow_mult else 1)
            file_lines = new_file_content.splitlines(keepends=True)

        diff = list(
            difflib.unified_diff(
                file_content.splitlines(keepends=True),
                new_file_content.splitlines(keepends=True),
                fromfile=f"a/{filepath}",
                tofile=f"b/{filepath}",
                n=3,
            )
        )

        if not diff:
            return "No changes detected."
            
        syntax_err = _validate_syntax(filepath, new_file_content)
        if syntax_err:
            return "Error: The edit introduces a syntax error and was aborted.\\n" + syntax_err

        console.print(
            Panel(
                f"[bold {Theme.ACCENT}]◆ AIZEN[/bold {Theme.ACCENT}] [{Theme.TEXT}]wants to edit:[/{Theme.TEXT}] [bold {Theme.ACCENT}]{filepath}[/bold {Theme.ACCENT}]",
                border_style=Theme.BORDER,
            )
        )
        _render_diff(diff, filepath)

        with terminal_lock:
            if not _ask_permission("  ▸ Apply edit?", auto_approve):
                return "User denied the edit."

        backup_manager.backup(filepath)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_file_content)

        return f"✓ Successfully applied {len(replacement_chunks)} replacement(s) to {filepath}"
    except Exception as e:
        return f"Error editing file: {e}"

'''

execute_tool_idx = content.find("def execute_tool(")
if execute_tool_idx != -1:
    content = content[:execute_tool_idx] + new_funcs + "\n" + content[execute_tool_idx:]
else:
    content += "\n" + new_funcs

write_file_def = r'def write_file_with_diff\(filepath: str, content: str, auto_approve: bool = False\) -> str:'
new_write_file_def = 'def write_file_with_diff(filepath: str, content: str, auto_approve: bool = False, start_line: int = None, end_line: int = None) -> str:'
content = re.sub(write_file_def, new_write_file_def, content)

write_body_orig = '''        if os.path.exists(filepath):
            with open(filepath, encoding="utf-8", errors="ignore") as f:
                old_content = f.read()
            if old_content == content:
                return "No changes detected."
'''
write_body_new = '''        if os.path.exists(filepath):
            with open(filepath, encoding="utf-8", errors="ignore") as f:
                old_content = f.read()
                
            if start_line is not None and end_line is not None:
                lines = old_content.splitlines(keepends=True)
                sl = max(0, start_line - 1)
                el = min(len(lines), end_line)
                new_content = "".join(lines[:sl]) + content
                if not new_content.endswith("\\n") and lines[el:]:
                    new_content += "\\n"
                new_content += "".join(lines[el:])
                content = new_content

            if old_content == content:
                return "No changes detected."
'''
content = content.replace(write_body_orig, write_body_new)

dispatch_additions = '''
    elif func_name == "replace_file_content":
        filepath = str(args.get("filepath", ""))
        target = str(args.get("target_content", ""))
        replacement = str(args.get("replacement_content", ""))
        sl = int(args.get("start_line", 1))
        el = int(args.get("end_line", 999999))
        am = bool(args.get("allow_multiple", False))
        tool_label.append(f" → {filepath or '?'}", style="dim")
        console.print(tool_label)
        return replace_file_content(filepath, target, replacement, sl, el, am, auto_approve=auto_approve)

    elif func_name == "multi_replace_file_content":
        filepath = str(args.get("filepath", ""))
        chunks = args.get("replacement_chunks", [])
        tool_label.append(f" → {filepath or '?'} ({len(chunks)} chunks)", style="dim")
        console.print(tool_label)
        return multi_replace_file_content(filepath, chunks, auto_approve=auto_approve)
'''

edit_file_branch = r'    elif func_name == "edit_file":.*?return edit_file\(filepath, old_content, new_content, auto_approve=auto_approve\)'
content = re.sub(edit_file_branch, lambda m: m.group(0) + "\n" + dispatch_additions, content, flags=re.DOTALL)

write_file_dispatch = r'    elif func_name == "write_file":\s*filepath = str\(args\.get\("filepath", ""\)\)\s*content = str\(args\.get\("content", ""\)\)\s*tool_label\.append\(f" → \{filepath or \'\?\'\}", style="dim"\)\s*console\.print\(tool_label\)\s*return write_file_with_diff\(filepath, content, auto_approve=auto_approve\)'
new_write_file_dispatch = '''    elif func_name == "write_file":
        filepath = str(args.get("filepath", ""))
        fcontent = str(args.get("content", ""))
        sl = args.get("start_line")
        el = args.get("end_line")
        tool_label.append(f" → {filepath or '?'}", style="dim")
        console.print(tool_label)
        return write_file_with_diff(filepath, fcontent, auto_approve=auto_approve, start_line=sl, end_line=el)'''
content = re.sub(write_file_dispatch, new_write_file_dispatch, content, flags=re.DOTALL)

with open("aizen/tools.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Patch 2 done")
