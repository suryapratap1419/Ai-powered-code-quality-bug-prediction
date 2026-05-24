import re
from .base_analyzer import BaseAnalyzer

class JavaAnalyzer(BaseAnalyzer):
    
    def extract_metrics(self, code):
        metrics = {
            'lines_of_code': len(code.split('\n')),
            'functions': 0,
            'classes': 0,
            'loops': 0,
            'conditionals': 0,
            'comments': 0,
            'imports': 0
        }
        
        comment_symbols = {'single': ['//'], 'multi_start': None, 'multi_end': None}
        metrics['comments'] = self.count_comments(code, comment_symbols)
        
        method_pattern = r'(public|private|protected)?\s+\w+\s+(\w+)\s*\([^)]*\)\s*\{'
        metrics['functions'] = len(re.findall(method_pattern, code))
        metrics['classes'] = len(re.findall(r'class\s+(\w+)', code))
        metrics['loops'] = len(re.findall(r'\b(for|while)\s*\(', code))
        metrics['conditionals'] = len(re.findall(r'\b(if|else if|switch)\s*\(', code))
        metrics['imports'] = len(re.findall(r'^import\s+', code, re.MULTILINE))
        
        return metrics
    
    def detect_bugs(self, code, metrics):
        bugs = []
        lines = code.split('\n')
        
        # Remove comments
        clean_lines = []
        for line in lines:
            comment_pos = line.find('//')
            if comment_pos != -1:
                line = line[:comment_pos]
            clean_lines.append(line)
        
        # Java keywords
        keywords = {
            'public', 'private', 'protected', 'class', 'static', 'void',
            'int', 'String', 'double', 'float', 'boolean', 'char', 'long',
            'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'break',
            'continue', 'return', 'new', 'try', 'catch', 'finally',
            'throw', 'throws', 'this', 'super', 'extends', 'implements',
            'import', 'package', 'true', 'false', 'null', 'instanceof',
            'System', 'out', 'println', 'print', 'main', 'args', 'length',
            'Test', 'Exception', 'RuntimeException', 'NullPointerException'
        }
        
        declared = set(keywords)
        methods = set()
        classes = set()
        
        # PASS 1: Collect declarations
        for i, line in enumerate(clean_lines, 1):
            stripped = line.strip()
            if not stripped:
                continue
            
            # Class names
            class_match = re.search(r'class\s+(\w+)', line)
            if class_match:
                classes.add(class_match.group(1))
                declared.add(class_match.group(1))
            
            # Method names
            method_match = re.search(r'(public|private|protected)?\s+\w+\s+(\w+)\s*\(', line)
            if method_match:
                methods.add(method_match.group(2))
                declared.add(method_match.group(2))
            
            # Variables
            var_patterns = [
                r'(int|String|double|float|boolean|char|long)\s+(\w+)\s*[=;]',
                r'for\s*\(\s*(int|long)\s+(\w+)\s*=',
                r'catch\s*\(\s*(\w+)\s+(\w+)\s*\)'
            ]
            
            for pattern in var_patterns:
                var_match = re.search(pattern, line)
                if var_match:
                    var_name = var_match.group(var_match.lastindex)
                    declared.add(var_name)
            
            # Method parameters
            param_match = re.search(r'\(([^)]*)\)', line)
            if param_match and ('public' in line or 'private' in line or 'protected' in line):
                params = param_match.group(1).split(',')
                for param in params:
                    parts = param.strip().split()
                    if len(parts) >= 2:
                        declared.add(parts[1])
        
        # PASS 2: Detect bugs
        in_function = False
        current_func = None
        current_func_line = None
        return_type = None
        brace_count = 0
        
        for i, line in enumerate(clean_lines, 1):
            stripped = line.strip()
            if not stripped:
                continue
            
            # ===== BUG: Missing semicolon =====
            if not stripped.endswith(';') and not stripped.endswith('{') and not stripped.endswith('}') and not stripped.startswith('//'):
                if not stripped.startswith('@') and not stripped.startswith('import') and not stripped.startswith('/*'):
                    if stripped and not stripped.startswith('return'):
                        bugs.append({
                            'line': i,
                            'type': 'SYNTAX',
                            'severity': 'CRITICAL',
                            'message': "Missing semicolon",
                            'suggestion': "Add ; at end of line"
                        })
            
            # ===== BUG: Infinite loop (i--) =====
            if 'for' in line and 'i--' in line:
                bugs.append({
                    'line': i,
                    'type': 'LOGIC',
                    'severity': 'HIGH',
                    'message': "Infinite loop: using i-- in for loop",
                    'suggestion': "Change i-- to i++"
                })
            
            # ===== BUG: Off-by-one (<= length) =====
            if re.search(r'i\s*<=\s*\w+\.length', line):
                bugs.append({
                    'line': i,
                    'type': 'RUNTIME',
                    'severity': 'CRITICAL',
                    'message': "Array index out of bounds: using <= with .length",
                    'suggestion': "Use i < arr.length instead"
                })
            
            # ===== BUG: Assignment in if =====
            if re.search(r'if\s*\(\s*\w+\s*=\s*\w+', line):
                bugs.append({
                    'line': i,
                    'type': 'LOGIC',
                    'severity': 'HIGH',
                    'message': "Assignment in if condition (should be comparison)",
                    'suggestion': "Use == instead of ="
                })
            
            # ===== BUG: Empty catch block =====
            if 'catch' in line and '{' in line:
                for j in range(1, 5):
                    if i + j < len(clean_lines):
                        next_line = clean_lines[i + j].strip()
                        if next_line == '}':
                            bugs.append({
                                'line': i,
                                'type': 'EXCEPTION',
                                'severity': 'MEDIUM',
                                'message': "Empty catch block",
                                'suggestion': "Handle exception or log it"
                            })
                            break
            
            # ===== BUG: Missing return in non-void =====
            if ('public static int' in line or 'public int' in line) and '{' in line:
                return_type = line.split()[2] if 'public static int' in line else line.split()[1]
                in_function = True
                current_func_line = i
                brace_count = 1
                continue
            
            if in_function:
                brace_count += line.count('{') - line.count('}')
                if brace_count == 0:
                    has_return = False
                    for j in range(current_func_line, i):
                        if 'return' in clean_lines[j]:
                            has_return = True
                            break
                    if not has_return and return_type != 'void':
                        bugs.append({
                            'line': current_func_line,
                            'type': 'RUNTIME',
                            'severity': 'HIGH',
                            'message': f"Missing return statement",
                            'suggestion': f"Add return statement with appropriate value"
                        })
                    in_function = False
                    return_type = None
            
            # ===== BUG: Division by zero =====
            if '/ 0' in line or '/0' in line:
                bugs.append({
                    'line': i,
                    'type': 'RUNTIME',
                    'severity': 'CRITICAL',
                    'message': "Division by zero detected",
                    'suggestion': "Add zero check before division"
                })
            
            # ===== BUG: Null pointer =====
            if '= null' in line and '.' in line.split(';')[0]:
                var_name = re.search(r'(\w+)\s*=\s*null', line)
                if var_name:
                    var = var_name.group(1)
                    for j in range(i, min(i + 10, len(clean_lines))):
                        if f'{var}.' in clean_lines[j]:
                            bugs.append({
                                'line': i,
                                'type': 'RUNTIME',
                                'severity': 'HIGH',
                                'message': f"Null pointer risk: '{var}' is null",
                                'suggestion': f"Add null check before using '{var}'"
                            })
                            break
            
            # ===== BUG: Infinite while loop =====
            if 'while' in line and '(' in line:
                var_match = re.search(r'while\s*\(\s*(\w+)\s*[<>=!]+\s*\d+\s*\)', line)
                if var_match:
                    loop_var = var_match.group(1)
                    has_increment = False
                    for j in range(i, min(i + 15, len(clean_lines))):
                        if f'{loop_var}++' in clean_lines[j] or f'++{loop_var}' in clean_lines[j]:
                            has_increment = True
                            break
                    if not has_increment:
                        bugs.append({
                            'line': i,
                            'type': 'LOGIC',
                            'severity': 'HIGH',
                            'message': f"Infinite while loop: '{loop_var}' never incremented",
                            'suggestion': f"Add {loop_var}++ inside the loop"
                        })
            
            # ===== BUG: Array index error (arr[5]) =====
            array_access = re.search(r'(\w+)\[(\d+)\]', line)
            if array_access:
                arr_name = array_access.group(1)
                index = int(array_access.group(2))
                if index > 10:
                    bugs.append({
                        'line': i,
                        'type': 'RUNTIME',
                        'severity': 'CRITICAL',
                        'message': f"Array index {index} may be out of bounds",
                        'suggestion': f"Check array size before accessing index {index}"
                    })
            
            # ===== BUG: Undefined variables =====
            words = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', line)
            for word in words:
                if word in keywords or word in declared:
                    continue
                if f'{word} =' in line or f'{word}=' in line:
                    continue
                if word.isdigit():
                    continue
                if len(word) == 1 and word in ['i', 'j', 'k', 'x', 'y', 'z']:
                    continue
                
                bugs.append({
                    'line': i,
                    'type': 'RUNTIME',
                    'severity': 'CRITICAL',
                    'message': f"Variable '{word}' may be undefined",
                    'suggestion': f"Declare '{word}' before using it"
                })
                declared.add(word)
        
        # Remove duplicates
        unique_bugs = []
        seen = set()
        for bug in bugs:
            key = (bug['line'], bug.get('type', ''))
            if key not in seen:
                seen.add(key)
                unique_bugs.append(bug)
        
        return unique_bugs