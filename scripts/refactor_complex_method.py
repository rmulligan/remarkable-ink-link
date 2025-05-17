#!/usr/bin/env python3
"""Refactor complex method in syntax_highlight_compiler.py"""


def refactor_simple_tokenize():
    """Generate refactored version of _simple_tokenize method."""

    refactored_code = '''
    def _simple_tokenize(self, code: str) -> List[Token]:
        """Simple tokenizer fallback for languages without a scanner."""
        tokens = []
        position = 0
        lines = code.split("\n")

        for line_num, line in enumerate(lines, 1):
            tokens.extend(self._tokenize_line(line, line_num, position))
            position += len(line) + 1  # +1 for newline

        return tokens

    def _tokenize_line(self, line: str, line_num: int, position: int) -> List[Token]:
        """Tokenize a single line of code."""
        tokens = []
        i = 0

        while i < len(line):
            # Try each tokenizer in order
            for tokenizer in [
                self._tokenize_whitespace,
                self._tokenize_comment,
                self._tokenize_string,
                self._tokenize_number,
                self._tokenize_identifier_or_keyword,
                self._tokenize_operator,
                self._tokenize_punctuation,
            ]:
                result = tokenizer(line, i, line_num, position)
                if result:
                    token, new_i = result
                    tokens.append(token)
                    i = new_i
                    break

        return tokens

    def _tokenize_whitespace(self, line: str, i: int, line_num: int, position: int) -> Optional[Tuple[Token, int]]:
        """Tokenize whitespace."""
        if not line[i].isspace():
            return None

        start = i
        while i < len(line) and line[i].isspace():
            i += 1

        token = Token(
            type=TokenType.WHITESPACE,
            value=line[start:i],
            start=position + start,
            end=position + i,
            line=line_num,
            column=start + 1,
        )
        return token, i

    def _tokenize_comment(self, line: str, i: int, line_num: int, position: int) -> Optional[Tuple[Token, int]]:
        """Tokenize comments."""
        if not (self.current_language.line_comment and
                line[i:].startswith(self.current_language.line_comment)):
            return None

        token = Token(
            type=TokenType.COMMENT,
            value=line[i:],
            start=position + i,
            end=position + len(line),
            line=line_num,
            column=i + 1,
        )
        return token, len(line)  # Comments consume rest of line

    def _tokenize_string(self, line: str, i: int, line_num: int, position: int) -> Optional[Tuple[Token, int]]:
        """Tokenize string literals."""
        if line[i] not in ['"', "'"]:
            return None

        quote = line[i]
        start = i
        i += 1

        while i < len(line) and line[i] != quote:
            if line[i] == "\\":
                i += 2
            else:
                i += 1

        if i < len(line):
            i += 1

        token = Token(
            type=TokenType.STRING,
            value=line[start:i],
            start=position + start,
            end=position + i,
            line=line_num,
            column=start + 1,
        )
        return token, i

    def _tokenize_number(self, line: str, i: int, line_num: int, position: int) -> Optional[Tuple[Token, int]]:
        """Tokenize numeric literals."""
        if not line[i].isdigit():
            return None

        start = i
        while i < len(line) and (line[i].isdigit() or line[i] == "."):
            i += 1

        token = Token(
            type=TokenType.NUMBER,
            value=line[start:i],
            start=position + start,
            end=position + i,
            line=line_num,
            column=start + 1,
        )
        return token, i

    def _tokenize_identifier_or_keyword(self, line: str, i: int, line_num: int, position: int) -> Optional[Tuple[Token, int]]:
        """Tokenize identifiers and keywords."""
        if not (line[i].isalpha() or line[i] == "_"):
            return None

        start = i
        while i < len(line) and (line[i].isalnum() or line[i] == "_"):
            i += 1

        word = line[start:i]
        token_type = self._get_identifier_type(word)

        token = Token(
            type=token_type,
            value=word,
            start=position + start,
            end=position + i,
            line=line_num,
            column=start + 1,
        )
        return token, i

    def _get_identifier_type(self, word: str) -> TokenType:
        """Determine the type of an identifier."""
        if word in self.current_language.keywords:
            return TokenType.KEYWORD
        elif word in self.current_language.builtin_functions:
            return TokenType.BUILTIN
        else:
            return TokenType.IDENTIFIER

    def _tokenize_operator(self, line: str, i: int, line_num: int, position: int) -> Optional[Tuple[Token, int]]:
        """Tokenize operators."""
        # Try multi-character operators first
        for op_len in [3, 2, 1]:
            if i + op_len <= len(line):
                op = line[i : i + op_len]
                if op in self.current_language.operators:
                    token = Token(
                        type=TokenType.OPERATOR,
                        value=op,
                        start=position + i,
                        end=position + i + op_len,
                        line=line_num,
                        column=i + 1,
                    )
                    return token, i + op_len
        return None

    def _tokenize_punctuation(self, line: str, i: int, line_num: int, position: int) -> Optional[Tuple[Token, int]]:
        """Tokenize punctuation as fallback."""
        token = Token(
            type=TokenType.PUNCTUATION,
            value=line[i],
            start=position + i,
            end=position + i + 1,
            line=line_num,
            column=i + 1,
        )
        return token, i + 1
'''
    return refactored_code


if __name__ == "__main__":
    print(refactor_simple_tokenize())
