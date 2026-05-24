import re
from .base_analyzer import BaseAnalyzer

class CppAnalyzer(BaseAnalyzer):
    
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
        
        function_pattern = r'\b(int|void|char|float|double|bool|long|short|auto|string)\s+(\w+)\s*\([^)]*\)\s*\{'
        metrics['functions'] = len(re.findall(function_pattern, code))
        metrics['classes'] = len(re.findall(r'class\s+(\w+)', code))
        metrics['loops'] = len(re.findall(r'\b(for|while|do)\s*\(', code))
        metrics['conditionals'] = len(re.findall(r'\b(if|else if|switch)\s*\(', code))
        metrics['imports'] = len(re.findall(r'#include', code))
        
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
        
        # C++ keywords and built-ins (SAFE)
        safe_keywords = {
            'std', 'cout', 'cin', 'endl', 'cerr', 'clog', 'NULL', 'nullptr',
            'vector', 'string', 'map', 'set', 'list', 'queue', 'stack',
            'pair', 'tuple', 'array', 'deque', 'iostream', 'fstream',
            'sstream', 'algorithm', 'iterator', 'memory', 'thread', 'mutex',
            'int', 'void', 'char', 'float', 'double', 'bool', 'long', 'short',
            'auto', 'const', 'static', 'virtual', 'inline', 'friend',
            'public', 'private', 'protected', 'class', 'struct', 'enum',
            'namespace', 'using', 'template', 'typename', 'this', 'new',
            'delete', 'if', 'else', 'for', 'while', 'do', 'switch', 'case',
            'break', 'continue', 'return', 'goto', 'try', 'catch', 'throw',
            'true', 'false', 'include', 'define', 'main'
        }
        
        declared = set(safe_keywords)
        functions = set()
        
        # ==========================================
        # PASS 1: COLLECT DECLARATIONS
        # ==========================================
        for i, line in enumerate(clean_lines, 1):
            stripped = line.strip()
            if not stripped:
                continue
            
            # Function declarations
            func_match = re.search(r'\b(int|void|char|float|double|bool|long|short|auto|string)\s+(\w+)\s*\(', line)
            if func_match:
                functions.add(func_match.group(2))
                declared.add(func_match.group(2))
            
            # Variable declarations
            var_patterns = [
                r'\b(int|float|double|char|bool|long|short|auto|string)\s+(\w+)\s*[=;]',
                r'\b(int|float|double|char|bool|long|short|auto|string)\s+(\w+)\s*\[',
                r'for\s*\(\s*(int|auto)\s+(\w+)\s*='
            ]
            
            for pattern in var_patterns:
                var_match = re.search(pattern, line)
                if var_match:
                    var_name = var_match.group(var_match.lastindex)
                    declared.add(var_name)
            
            # Multiple declarations (int a, b, c;)
            multi_decl = re.findall(r'\b(int|float|double|char)\s+(\w+)\s*,', line)
            for _, var_name in multi_decl:
                declared.add(var_name)
            
            # Pointer declarations
            ptr_match = re.search(r'\w+\s*\*\s*(\w+)', line)
            if ptr_match and 'return' not in line:
                declared.add(ptr_match.group(1))
            
            # Function parameters
            if '(' in line and ')' in line:
                param_match = re.search(r'\(([^)]*)\)', line)
                if param_match and ('int' in line or 'void' in line or 'char' in line):
                    params = param_match.group(1).split(',')
                    for param in params:
                        parts = param.strip().split()
                        if len(parts) >= 2:
                            declared.add(parts[1])
                        elif len(parts) == 1 and parts[0]:
                            declared.add(parts[0])
        
        # ==========================================
        # PASS 2: DETECT BUGS
        # ==========================================
        
        # BUG 1: using namespace std
        for i, line in enumerate(lines, 1):
            if 'using namespace std' in line:
                bugs.append({
                    'line': i,
                    'type': 'STYLE',
                    'severity': 'LOW',
                    'message': "Using namespace std is bad practice",
                    'suggestion': "Use std:: prefix instead (std::cout, std::cin)"
                })
        
        # BUG 2: Local variable naming (global)
        for i, line in enumerate(clean_lines, 1):
            if re.search(r'^int\s+[a-z][A-Z]', line):
                bugs.append({
                    'line': i,
                    'type': 'STYLE',
                    'severity': 'LOW',
                    'message': "Global variable detected (bad practice)",
                    'suggestion': "Avoid global variables, use local variables or pass as parameters"
                })
        
        # BUG 3: Infinite loop (i-- in for loop)
        for i, line in enumerate(clean_lines, 1):
            if 'for' in line and 'i--' in line:
                bugs.append({
                    'line': i,
                    'type': 'LOGIC',
                    'severity': 'HIGH',
                    'message': "Infinite loop: using i-- in for loop",
                    'suggestion': "Change i-- to i++"
                })
        
        # BUG 4: Division by zero
        for i, line in enumerate(clean_lines, 1):
            if '/ 0' in line or '/0' in line:
                bugs.append({
                    'line': i,
                    'type': 'RUNTIME',
                    'severity': 'CRITICAL',
                    'message': "Division by zero detected",
                    'suggestion': "Add check for zero before division"
                })
        
        # BUG 5: Off-by-one (<= size)
        for i, line in enumerate(clean_lines, 1):
            if re.search(r'i\s*<=\s*\w+', line) and 'size' in line:
                bugs.append({
                    'line': i,
                    'type': 'RUNTIME',
                    'severity': 'CRITICAL',
                    'message': "Off-by-one error: using <= with array size",
                    'suggestion': "Use i < size instead of i <= size"
                })
        
        # BUG 6: Empty catch block
        for i, line in enumerate(clean_lines, 1):
            if 'catch' in line and '{' in line:
                for j in range(1, 5):
                    if i + j < len(clean_lines):
                        next_line = clean_lines[i + j].strip()
                        if next_line == '}' or next_line == '// empty catch':
                            bugs.append({
                                'line': i,
                                'type': 'EXCEPTION',
                                'severity': 'MEDIUM',
                                'message': "Empty catch block",
                                'suggestion': "Handle exception or log it"
                            })
                            break
        
        # BUG 7: Infinite while loop
        for i, line in enumerate(clean_lines, 1):
            while_match = re.search(r'while\s*\(\s*(\w+)\s*[<>=!]+\s*\d+\s*\)', line)
            if while_match:
                loop_var = while_match.group(1)
                has_increment = False
                for j in range(i, min(i + 20, len(clean_lines))):
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
        
        # BUG 8: Missing return statement
        in_function = False
        current_func = None
        current_func_line = None
        return_type = None
        brace_count = 0
        
        for i, line in enumerate(clean_lines, 1):
            func_start = re.search(r'\b(int|void|char|float|double|bool|long|short|auto|string)\s+(\w+)\s*\([^)]*\)\s*\{', line)
            if func_start:
                in_function = True
                current_func = func_start.group(2)
                current_func_line = i
                return_type = func_start.group(1)
                brace_count = 1
                continue
            
            if in_function:
                brace_count += line.count('{') - line.count('}')
                if brace_count == 0:
                    if return_type != 'void':
                        has_return = False
                        for j in range(current_func_line, i):
                            if 'return' in clean_lines[j]:
                                has_return = True
                                break
                        if not has_return and current_func != 'main':
                            bugs.append({
                                'line': current_func_line,
                                'type': 'RUNTIME',
                                'severity': 'HIGH',
                                'message': f"Function '{current_func}' returns {return_type} but has no return statement",
                                'suggestion': f"Add 'return value;' at end of function"
                            })
                    in_function = False
                    current_func = None
                    return_type = None
        
        # BUG 9: Memory leak (new without delete)
        for i, line in enumerate(clean_lines, 1):
            if 'new ' in line and 'delete' not in line:
                has_delete = False
                for j in range(i, min(i + 30, len(clean_lines))):
                    if 'delete' in clean_lines[j]:
                        has_delete = True
                        break
                if not has_delete and 'shared_ptr' not in line and 'unique_ptr' not in line:
                    bugs.append({
                        'line': i,
                        'type': 'MEMORY',
                        'severity': 'MEDIUM',
                        'message': "Potential memory leak: 'new' without matching 'delete'",
                        'suggestion': "Use smart pointers (unique_ptr, shared_ptr) or add delete"
                    })
        
        # BUG 10: Null pointer
        for i, line in enumerate(clean_lines, 1):
            if 'nullptr' in line and '*' in line:
                ptr_match = re.search(r'\w+\s*\*\s*(\w+)\s*=\s*nullptr', line)
                if ptr_match:
                    ptr_name = ptr_match.group(1)
                    for j in range(i, min(i + 15, len(clean_lines))):
                        if f'{ptr_name}[' in clean_lines[j] or f'*{ptr_name}' in clean_lines[j] or f'{ptr_name}->' in clean_lines[j]:
                            bugs.append({
                                'line': i,
                                'type': 'RUNTIME',
                                'severity': 'CRITICAL',
                                'message': f"Null pointer: '{ptr_name}' is set to nullptr then dereferenced",
                                'suggestion': f"Add if({ptr_name} != nullptr) check before dereferencing"
                            })
                            break
        
        # BUG 11: Array index error
        for i, line in enumerate(clean_lines, 1):
            array_match = re.search(r'(\w+)\[(\d+)\]', line)
            if array_match:
                arr_name = array_match.group(1)
                index = int(array_match.group(2))
                # Look for array declaration
                for j in range(max(0, i-30), i):
                    if f'int {arr_name}[' in clean_lines[j] or f'int {arr_name} []' in clean_lines[j]:
                        size_match = re.search(r'\[(\d+)\]', clean_lines[j])
                        if size_match:
                            size = int(size_match.group(1))
                            if index >= size:
                                bugs.append({
                                    'line': i,
                                    'type': 'RUNTIME',
                                    'severity': 'CRITICAL',
                                    'message': f"Array index {index} out of bounds (size {size})",
                                    'suggestion': f"Use index < {size}"
                                })
                        break
        
        # BUG 12: Undefined variable
        for i, line in enumerate(clean_lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('//'):
                continue
            if stripped.startswith('int ') or stripped.startswith('void ') or stripped.startswith('cout'):
                continue
            
            line_clean = re.sub(r'(["\']).*?\1', '', line)
            words = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', line_clean)
            
            for word in words:
                if word in safe_keywords or word in declared:
                    continue
                if f'{word} =' in line or f'{word}=' in line:
                    continue
                if word.isdigit():
                    continue
                if len(word) == 1 and word in ['i', 'j', 'k', 'x', 'y', 'z']:
                    continue
                if word in functions:
                    continue
                
                bugs.append({
                    'line': i,
                    'type': 'RUNTIME',
                    'severity': 'HIGH',
                    'message': f"Variable '{word}' is used but not defined",
                    'suggestion': f"Declare '{word}' before using it"
                })
                declared.add(word)
        
        # BUG 13: Uninitialized variable
        for i, line in enumerate(clean_lines, 1):
            if re.search(r'int\s+(\w+)\s*;', line) and '=' not in line:
                var_name = re.search(r'int\s+(\w+)\s*;', line)
                if var_name:
                    var = var_name.group(1)
                    for j in range(i, min(i + 10, len(clean_lines))):
                        if f'cout << {var}' in clean_lines[j] or f'{var} =' not in clean_lines[j]:
                            bugs.append({
                                'line': i,
                                'type': 'RUNTIME',
                                'severity': 'MEDIUM',
                                'message': f"Uninitialized variable '{var}'",
                                'suggestion': f"Initialize '{var}' when declaring: int {var} = 0;"
                            })
                            break
        
        # Remove duplicates
        unique_bugs = []
        seen = set()
        for bug in bugs:
            key = (bug['line'], bug.get('type', ''))
            if key not in seen:
                seen.add(key)
                unique_bugs.append(bug)
        
        return unique_bugs