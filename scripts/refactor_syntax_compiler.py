#!/usr/bin/env python3
"""Apply refactoring to syntax_highlight_compiler.py"""

import re

# Read the original file
with open("src/inklink/services/syntax_highlight_compiler.py", "r") as f:
    content = f.read()

# Find the method boundaries
start_pattern = r"(\s*)def _simple_tokenize\(self, code: str\) -> List\[Token\]:"
end_pattern = r"\n(\s*)def "

match_start = re.search(start_pattern, content)
if not match_start:
    print("Could not find _simple_tokenize method")
    exit(1)

# Find where the method ends (next method or end of class)
remaining_content = content[match_start.end() :]
match_end = re.search(end_pattern, remaining_content)

if match_end:
    method_end = match_start.end() + match_end.start()
else:
    # Method goes to end of file/class
    method_end = len(content)

indent = match_start.group(1)

# Create the refactored methods
refactored_methods = f'''
{indent}def _simple_tokenize(self, code: str) -> List[Token]:
{indent}    """Simple tokenizer fallback for languages without a scanner."""
{indent}    tokens = []
{indent}    position = 0
{indent}    lines = code.split("\\n")

{indent}    for line_num, line in enumerate(lines, 1):
{indent}        tokens.extend(self._tokenize_line(line, line_num, position))
{indent}        position += len(line) + 1  # +1 for newline

{indent}    return tokens

{indent}def _tokenize_line(self, line: str, line_num: int, position: int) -> List[Token]:
{indent}    """Tokenize a single line of code."""
{indent}    tokens = []
{indent}    i = 0

{indent}    while i < len(line):
{indent}        # Try each tokenizer in order
{indent}        for tokenizer in [
{indent}            self._tokenize_whitespace,
{indent}            self._tokenize_comment,
{indent}            self._tokenize_string,
{indent}            self._tokenize_number,
{indent}            self._tokenize_identifier_or_keyword,
{indent}            self._tokenize_operator,
{indent}            self._tokenize_punctuation,
{indent}        ]:
{indent}            result = tokenizer(line, i, line_num, position)
{indent}            if result:
{indent}                token, new_i = result
{indent}                tokens.append(token)
{indent}                i = new_i
{indent}                break

{indent}    return tokens

{indent}def _tokenize_whitespace(self, line: str, i: int, line_num: int, position: int) -> Optional[Tuple[Token, int]]:
{indent}    """Tokenize whitespace."""
{indent}    if not line[i].isspace():
{indent}        return None
{indent}
{indent}    start = i
{indent}    while i < len(line) and line[i].isspace():
{indent}        i += 1
{indent}
{indent}    token = Token(
{indent}        type=TokenType.WHITESPACE,
{indent}        value=line[start:i],
{indent}        start=position + start,
{indent}        end=position + i,
{indent}        line=line_num,
{indent}        column=start + 1,
{indent}    )
{indent}    return token, i

{indent}def _tokenize_comment(self, line: str, i: int, line_num: int, position: int) -> Optional[Tuple[Token, int]]:
{indent}    """Tokenize comments."""
{indent}    if not (self.current_language.line_comment and
{indent}            line[i:].startswith(self.current_language.line_comment)):
{indent}        return None
{indent}
{indent}    token = Token(
{indent}        type=TokenType.COMMENT,
{indent}        value=line[i:],
{indent}        start=position + i,
{indent}        end=position + len(line),
{indent}        line=line_num,
{indent}        column=i + 1,
{indent}    )
{indent}    return token, len(line)  # Comments consume rest of line

{indent}def _tokenize_string(self, line: str, i: int, line_num: int, position: int) -> Optional[Tuple[Token, int]]:
{indent}    """Tokenize string literals."""
{indent}    if line[i] not in ['"', "'"]:
{indent}        return None
{indent}
{indent}    quote = line[i]
{indent}    start = i
{indent}    i += 1
{indent}
{indent}    while i < len(line) and line[i] != quote:
{indent}        if line[i] == "\\\\":
{indent}            i += 2
{indent}        else:
{indent}            i += 1
{indent}
{indent}    if i < len(line):
{indent}        i += 1
{indent}
{indent}    token = Token(
{indent}        type=TokenType.STRING,
{indent}        value=line[start:i],
{indent}        start=position + start,
{indent}        end=position + i,
{indent}        line=line_num,
{indent}        column=start + 1,
{indent}    )
{indent}    return token, i

{indent}def _tokenize_number(self, line: str, i: int, line_num: int, position: int) -> Optional[Tuple[Token, int]]:
{indent}    """Tokenize numeric literals."""
{indent}    if not line[i].isdigit():
{indent}        return None
{indent}
{indent}    start = i
{indent}    while i < len(line) and (line[i].isdigit() or line[i] == "."):
{indent}        i += 1
{indent}
{indent}    token = Token(
{indent}        type=TokenType.NUMBER,
{indent}        value=line[start:i],
{indent}        start=position + start,
{indent}        end=position + i,
{indent}        line=line_num,
{indent}        column=start + 1,
{indent}    )
{indent}    return token, i

{indent}def _tokenize_identifier_or_keyword(self, line: str, i: int, line_num: int, position: int) -> Optional[Tuple[Token, int]]:
{indent}    """Tokenize identifiers and keywords."""
{indent}    if not (line[i].isalpha() or line[i] == "_"):
{indent}        return None
{indent}
{indent}    start = i
{indent}    while i < len(line) and (line[i].isalnum() or line[i] == "_"):
{indent}        i += 1
{indent}
{indent}    word = line[start:i]
{indent}    token_type = self._get_identifier_type(word)
{indent}
{indent}    token = Token(
{indent}        type=token_type,
{indent}        value=word,
{indent}        start=position + start,
{indent}        end=position + i,
{indent}        line=line_num,
{indent}        column=start + 1,
{indent}    )
{indent}    return token, i

{indent}def _get_identifier_type(self, word: str) -> TokenType:
{indent}    """Determine the type of an identifier."""
{indent}    if word in self.current_language.keywords:
{indent}        return TokenType.KEYWORD
{indent}    elif word in self.current_language.builtin_functions:
{indent}        return TokenType.BUILTIN
{indent}    else:
{indent}        return TokenType.IDENTIFIER

{indent}def _tokenize_operator(self, line: str, i: int, line_num: int, position: int) -> Optional[Tuple[Token, int]]:
{indent}    """Tokenize operators."""
{indent}    # Try multi-character operators first
{indent}    for op_len in [3, 2, 1]:
{indent}        if i + op_len <= len(line):
{indent}            op = line[i : i + op_len]
{indent}            if op in self.current_language.operators:
{indent}                token = Token(
{indent}                    type=TokenType.OPERATOR,
{indent}                    value=op,
{indent}                    start=position + i,
{indent}                    end=position + i + op_len,
{indent}                    line=line_num,
{indent}                    column=i + 1,
{indent}                )
{indent}                return token, i + op_len
{indent}    return None

{indent}def _tokenize_punctuation(self, line: str, i: int, line_num: int, position: int) -> Optional[Tuple[Token, int]]:
{indent}    """Tokenize punctuation as fallback."""
{indent}    token = Token(
{indent}        type=TokenType.PUNCTUATION,
{indent}        value=line[i],
{indent}        start=position + i,
{indent}        end=position + i + 1,
{indent}        line=line_num,
{indent}        column=i + 1,
{indent}    )
{indent}    return token, i + 1'''

# Replace the method in the content
new_content = (
    content[: match_start.start()] + refactored_methods + "\n" + content[method_end:]
)

# Write the updated content
with open("src/inklink/services/syntax_highlight_compiler.py", "w") as f:
    f.write(new_content)

print("Refactored syntax_highlight_compiler.py successfully")
