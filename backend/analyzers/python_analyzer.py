import ast
import builtins
from .base_analyzer import BaseAnalyzer

def add_parents(node, parent=None):
    for child in ast.iter_child_nodes(node):
        child.parent = parent
        add_parents(child, node)

class PythonAnalyzer(BaseAnalyzer):
    
    def extract_metrics(self, code):
        metrics = {
            'lines_of_code': self.count_lines(code),
            'functions': 0,
            'classes': 0,
            'loops': 0,
            'conditionals': 0,
            'comments': 0,
            'imports': 0
        }
        
        comment_symbols = {'single': ['#'], 'multi_start': None, 'multi_end': None}
        metrics['comments'] = self.count_comments(code, comment_symbols)
        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef): metrics['functions'] += 1
                elif isinstance(node, ast.ClassDef): metrics['classes'] += 1
                elif isinstance(node, (ast.For, ast.While, ast.comprehension)): metrics['loops'] += 1
                elif isinstance(node, ast.If): 
                    metrics['conditionals'] += 1
                    if node.orelse: metrics['conditionals'] += 1
                elif isinstance(node, (ast.Import, ast.ImportFrom)): metrics['imports'] += 1
        except: pass
        return metrics
    
    def detect_bugs(self, code, metrics):
        bugs = []
        
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            bugs.append({'line': e.lineno or 1, 'type': 'SYNTAX', 'severity': 'CRITICAL',
                        'message': f"Syntax error: {str(e)}", 'suggestion': "Fix the syntax error"})
            return bugs
        
        try:
            tree = ast.parse(code)
            add_parents(tree)
            
            defined = set(dir(builtins))
            defined.update(['self', 'cls', 'True', 'False', 'None', '__name__'])
            safe_loop_vars = {'i', 'j', 'k', 'x', 'y', 'z', 'item', 'value', 'key'}
            
            # COLLECT DEFINITIONS
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        defined.add(alias.name)
                        if alias.asname: defined.add(alias.asname)
                elif isinstance(node, ast.ImportFrom):
                    if node.module: defined.add(node.module.split('.')[0])
                    for alias in node.names:
                        if alias.name != '*':
                            defined.add(alias.name)
                            if alias.asname: defined.add(alias.asname)
                elif isinstance(node, ast.FunctionDef):
                    defined.add(node.name)
                    for arg in node.args.args: defined.add(arg.arg)
                elif isinstance(node, ast.ClassDef): defined.add(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name): defined.add(target.id)
                elif isinstance(node, ast.For):
                    if isinstance(node.target, ast.Name): defined.add(node.target.id)
                elif isinstance(node, ast.ExceptHandler):
                    if node.name and isinstance(node.name, str): defined.add(node.name)
            
            # UNDEFINED VARIABLES
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    parent = getattr(node, 'parent', None)
                    if parent and isinstance(parent, (ast.Import, ast.ImportFrom)): continue
                    if node.id in safe_loop_vars and node.id not in defined: continue
                    if node.id in defined: continue
                    bugs.append({
                        'line': node.lineno,
                        'type': 'RUNTIME',
                        'severity': 'CRITICAL',
                        'message': f"Variable '{node.id}' is used but not defined",
                        'suggestion': f"Define '{node.id}' before using it"
                    })
            
            # OFF-BY-ONE FACTORIAL
            for node in ast.walk(tree):
                if isinstance(node, ast.For):
                    if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name):
                        if node.iter.func.id == 'range' and len(node.iter.args) >= 2:
                            start = node.iter.args[0]
                            end = node.iter.args[1]
                            if (isinstance(start, ast.Constant) and start.value == 1 and
                                isinstance(end, ast.Name)):
                                has_mult = any(isinstance(c, ast.Mult) for c in ast.walk(node))
                                if has_mult:
                                    bugs.append({
                                        'line': node.lineno,
                                        'type': 'LOGIC',
                                        'severity': 'HIGH',
                                        'message': "Off-by-one error: range should be range(1, n+1)",
                                        'suggestion': "Change to range(1, n+1)"
                                    })
            
            
            # INDEX ERROR - FIXED FOR range(len(arr)+1)
           
            for node in ast.walk(tree):
                # Check for range(0, len(arr) + 1)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id == 'range' and len(node.args) >= 2:
                        second_arg = node.args[1]
                        if isinstance(second_arg, ast.BinOp) and isinstance(second_arg.op, ast.Add):
                            if (isinstance(second_arg.left, ast.Call) and 
                                isinstance(second_arg.left.func, ast.Name) and
                                second_arg.left.func.id == 'len'):
                                if (isinstance(second_arg.right, ast.Constant) and 
                                    second_arg.right.value == 1):
                                    bugs.append({
                                        'line': node.lineno,
                                        'type': 'RUNTIME',
                                        'severity': 'CRITICAL',
                                        'message': "IndexError: range(0, len(arr)+1) causes index out of bounds",
                                        'suggestion': "Change to range(len(arr))"
                                    })
            
            # INFINITE LOOP
            for node in ast.walk(tree):
                if isinstance(node, ast.While):
                    has_mod = any(isinstance(c, (ast.AugAssign, ast.Assign)) for c in ast.walk(node))
                    if not has_mod:
                        bugs.append({
                            'line': node.lineno,
                            'type': 'LOGIC',
                            'severity': 'HIGH',
                            'message': "Possible infinite loop: loop variable never modified",
                            'suggestion': "Add increment/decrement inside loop"
                        })
            
            # DIVISION BY ZERO
            for node in ast.walk(tree):
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                    if isinstance(node.right, ast.Constant) and node.right.value == 0:
                        bugs.append({
                            'line': node.lineno,
                            'type': 'RUNTIME',
                            'severity': 'CRITICAL',
                            'message': "Division by zero detected",
                            'suggestion': "Add zero check before division"
                        })
            
            # BARE EXCEPT
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    bugs.append({
                        'line': node.lineno,
                        'type': 'EXCEPTION',
                        'severity': 'MEDIUM',
                        'message': "Bare except clause used",
                        'suggestion': "Specify exception type"
                    })
        
        except Exception as e:
            print(f"AST error: {e}")
        
        unique_bugs = []
        seen = set()
        for bug in bugs:
            key = (bug['line'], bug.get('type', ''))
            if key not in seen:
                seen.add(key)
                unique_bugs.append(bug)
        
        return unique_bugs