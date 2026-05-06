import ast
with open('backend/parser.py', encoding='utf-8') as f:
    src = f.read()
ast.parse(src)
print('Sintaxa OK')
