"""Small S-expression reader for the supported KiCad forms.

The observer creates a fresh parse tree from the emitted bytes. No scene graph or
intended net information is passed into this module.
"""

import re


class ParseError(ValueError):
    pass


_TOKEN = re.compile(r'\s*(\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+)', re.DOTALL)


def parse(source: str) -> list:
    tokens = []
    offset = 0
    while offset < len(source):
        match = _TOKEN.match(source, offset)
        if not match:
            if source[offset:].isspace():
                break
            raise ParseError(f"invalid token at offset {offset}")
        token = match.group(1)
        tokens.append(token)
        offset = match.end()
    if len(tokens) > 2_000_000:
        raise ParseError("expression too large")
    stack: list[list] = []
    root = None
    for token in tokens:
        if token == "(":
            if len(stack) >= 128:
                raise ParseError("expression too deep")
            node: list = []
            if stack:
                stack[-1].append(node)
            stack.append(node)
        elif token == ")":
            if not stack:
                raise ParseError("unmatched closing parenthesis")
            node = stack.pop()
            if not stack:
                if root is not None:
                    raise ParseError("multiple roots")
                root = node
        elif not stack:
            raise ParseError("atom outside root")
        elif token.startswith('"'):
            import json

            stack[-1].append(json.loads(token))
        else:
            stack[-1].append(token)
    if stack or root is None:
        raise ParseError("incomplete expression")
    return root


def children(node: list, tag: str) -> list[list]:
    return [x for x in node[1:] if isinstance(x, list) and x and x[0] == tag]


def one(node: list, tag: str) -> list:
    found = children(node, tag)
    if len(found) != 1:
        raise ParseError(f"expected one {tag}, found {len(found)}")
    return found[0]


def quote(value: str) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)
