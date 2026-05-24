import re
from .base_analyzer import BaseAnalyzer

class JavaScriptAnalyzer(BaseAnalyzer):

    def strip_multiline_comments(self, code):
        """Remove /* ... */ style comments from code"""
        return re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)

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

        # Count single-line AND multi-line comments
        comment_symbols = {
            'single': ['//'],
            'multi_start': '/*',
            'multi_end': '*/'
        }
        metrics['comments'] = self.count_comments(code, comment_symbols)

        # Count functions (including arrow functions)
        func_patterns = [
            r'function\s+(\w+)\s*\(',           # function foo()
            r'const\s+(\w+)\s*=\s*function',    # const foo = function
            r'const\s+(\w+)\s*=\s*[\(\w].*=>',  # const foo = () => / const foo = x =>
            r'let\s+(\w+)\s*=\s*[\(\w].*=>',    # let foo = () =>
            r'(\w+)\s*:\s*function\s*\(',        # object method: foo: function()
        ]
        for pattern in func_patterns:
            metrics['functions'] += len(re.findall(pattern, code))

        metrics['classes'] = len(re.findall(r'class\s+(\w+)', code))
        metrics['loops'] = len(re.findall(r'\b(for|while)\s*\(', code))
        metrics['conditionals'] = len(re.findall(r'\b(if|else if|switch)\s*\(', code))

        # FIX: Actually count imports
        metrics['imports'] = len(re.findall(r'^\s*import\s+', code, re.MULTILINE))

        return metrics

    def detect_bugs(self, code, metrics):
        bugs = []

        
        # STEP 0: Strip multi-line comments first
        
        code = self.strip_multiline_comments(code)
        lines = code.split('\n')

        
        # STEP 1: Remove single-line comments
        
        clean_lines = []
        for line in lines:
            comment_pos = line.find('//')
            if comment_pos != -1:
                line = line[:comment_pos]
            clean_lines.append(line)

      
        # JavaScript built-ins (NOT BUGS)
       
        built_ins = {
            'console', 'log', 'warn', 'error', 'info', 'debug',
            'window', 'document', 'Math', 'Array', 'Object',
            'String', 'Number', 'Boolean', 'Date', 'Promise',
            'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval',
            'JSON', 'RegExp', 'Map', 'Set', 'WeakMap', 'WeakSet',
            'parseInt', 'parseFloat', 'isNaN', 'isFinite',
            'fetch', 'URL', 'URLSearchParams', 'FormData',
            'localStorage', 'sessionStorage', 'navigator', 'location',
            'history', 'alert', 'confirm', 'prompt',
            'Symbol', 'Proxy', 'Reflect', 'Error',
            'length', 'prototype', 'constructor', 'toString', 'valueOf',
            'push', 'pop', 'shift', 'unshift', 'splice', 'slice',
            'map', 'filter', 'reduce', 'forEach', 'find', 'findIndex',
            'includes', 'indexOf', 'join', 'reverse', 'sort',
            'keys', 'values', 'entries', 'assign', 'freeze', 'create',
            'then', 'catch', 'finally', 'resolve', 'reject', 'all', 'race',
            'arguments', 'module', 'exports', 'require', 'process', '__dirname',
            'addEventListener', 'removeEventListener', 'querySelector',
            'querySelectorAll', 'getElementById', 'getElementsByClassName',
        }

        # Track declared variables
        declared = set(built_ins)

        
        # PASS 1: Collect ALL declarations
       
        for i, line in enumerate(clean_lines, 1):
            stripped = line.strip()
            if not stripped:
                continue

            # FIX: Regular variable declarations
            var_matches = re.findall(r'(?:let|const|var)\s+(\w+)\s*[=;,]', line)
            for var in var_matches:
                declared.add(var)

            # FIX: Destructuring - const { name, age } = user
            obj_destruct = re.findall(r'(?:const|let|var)\s*\{([^}]+)\}', line)
            for group in obj_destruct:
                for item in group.split(','):
                    # Handle renaming: { oldName: newName }
                    parts = item.strip().split(':')
                    var_name = parts[-1].strip().split('=')[0].strip()
                    if re.match(r'^\w+$', var_name):
                        declared.add(var_name)

            # FIX: Array destructuring - const [a, b] = arr
            arr_destruct = re.findall(r'(?:const|let|var)\s*\[([^\]]+)\]', line)
            for group in arr_destruct:
                for item in group.split(','):
                    var_name = item.strip().split('=')[0].strip()
                    if re.match(r'^\w+$', var_name):
                        declared.add(var_name)

            # Regular function declarations
            func_matches = re.findall(r'function\s+(\w+)\s*\(', line)
            for func in func_matches:
                declared.add(func)

            # FIX: Arrow functions - const foo = (x, y) => ...
            arrow_func_names = re.findall(r'(?:const|let|var)\s+(\w+)\s*=\s*[\(\w].*=>', line)
            for func in arrow_func_names:
                declared.add(func)

            # Regular function parameters
            param_match = re.search(r'function\s*\w*\s*\(([^)]*)\)', line)
            if param_match:
                for param in param_match.group(1).split(','):
                    param = param.strip().split('=')[0].strip()  # handle defaults
                    if param and re.match(r'^\w+$', param):
                        declared.add(param)

            # FIX: Arrow function parameters - const foo = (x, y) => ...
            arrow_params = re.findall(r'=\s*\(([^)]*)\)\s*=>', line)
            for group in arrow_params:
                for param in group.split(','):
                    param = param.strip().split('=')[0].strip()
                    if param and re.match(r'^\w+$', param):
                        declared.add(param)

            # FIX: Single param arrow - const foo = x => ...
            single_arrow = re.findall(r'=\s*(\w+)\s*=>', line)
            for param in single_arrow:
                declared.add(param)

            # FIX: Import declarations - import React from 'react'
            default_import = re.findall(r'import\s+(\w+)\s+from', line)
            for name in default_import:
                declared.add(name)

            # FIX: Named imports - import { useState, useEffect } from 'react'
            named_imports = re.findall(r'import\s*\{([^}]+)\}', line)
            for group in named_imports:
                for name in group.split(','):
                    # Handle aliasing: { foo as bar }
                    alias = name.strip().split(' as ')
                    declared.add(alias[-1].strip())

            # FIX: Namespace imports - import * as React from 'react'
            namespace_import = re.findall(r'import\s*\*\s*as\s+(\w+)', line)
            for name in namespace_import:
                declared.add(name)

            # For loop variables - for (let i = 0; ...)
            for_vars = re.findall(r'for\s*\(\s*(?:let|const|var)\s+(\w+)', line)
            for var in for_vars:
                declared.add(var)

            # Catch block variables - catch(err)
            catch_vars = re.findall(r'catch\s*\(\s*(\w+)\s*\)', line)
            for var in catch_vars:
                declared.add(var)

            # Class declarations
            class_names = re.findall(r'class\s+(\w+)', line)
            for cls in class_names:
                declared.add(cls)

        
        # PASS 2: Detect bugs
        
        keywords = {
            'if', 'else', 'for', 'while', 'return', 'function', 'const', 'let',
            'var', 'true', 'false', 'null', 'undefined', 'this', 'new',
            'typeof', 'instanceof', 'delete', 'try', 'catch', 'finally',
            'switch', 'case', 'break', 'continue', 'default',
            'in', 'of', 'import', 'export', 'from', 'as',
            'class', 'extends', 'super', 'static', 'get', 'set',
            'async', 'await', 'yield', 'void', 'do', 'debugger',
            'NaN', 'Infinity'
        }

        for i, line in enumerate(clean_lines, 1):
            stripped = line.strip()
            if not stripped:
                continue

            # Skip pure declaration lines
            if re.match(r'^\s*(function |class )', stripped):
                continue
            if re.match(r'^\s*(let |const |var )\w+\s*[=;]', stripped):
                continue

            # FIX: Remove string literals (including template literals)
            line_clean = re.sub(r'`[^`]*`', '', line)         # template literals
            line_clean = re.sub(r'"[^"]*"', '', line_clean)   # double quotes
            line_clean = re.sub(r"'[^']*'", '', line_clean)   # single quotes

            # FIX: Remove dot-notation to avoid flagging obj.property
            line_clean = re.sub(r'\.\w+', '', line_clean)

            # Find potential variable usages
            words = re.findall(r'\b([a-zA-Z_$][a-zA-Z0-9_$]*)\b', line_clean)

            for word in words:
                if word in keywords or word in declared:
                    continue
                # Skip if this is an assignment target on this line
                if re.search(rf'\b{re.escape(word)}\s*=(?!=)', line_clean):
                    declared.add(word)
                    continue

                bugs.append({
                    'line': i,
                    'type': 'RUNTIME',
                    'severity': 'HIGH',
                    'message': f"Variable '{word}' is used but not defined",
                    'suggestion': f"Declare '{word}' with let/const/var before using it"
                })
                declared.add(word)  # Avoid duplicate reports for same variable


        # BUG 1: Off-by-one error (i <= arr.length)

        for i, line in enumerate(clean_lines, 1):
            if re.search(r'\w+\s*<=\s*\w+\.length', line):
                bugs.append({
                    'line': i,
                    'type': 'LOGIC',
                    'severity': 'HIGH',
                    'message': "Off-by-one error: using <= with array.length",
                    'suggestion': "Use i < array.length instead of i <= array.length"
                })

        # BUG 2: Infinite loop (i-- in for loop)
        
        for i, line in enumerate(clean_lines, 1):
            if re.search(r'for\s*\(', line) and 'i--' in line:
                bugs.append({
                    'line': i,
                    'type': 'LOGIC',
                    'severity': 'HIGH',
                    'message': "Infinite loop: decrementing counter in ascending for loop",
                    'suggestion': "Change i-- to i++ if iterating forward"
                })

        
        # BUG 3: Assignment in if condition
        
        for i, line in enumerate(clean_lines, 1):
            # Make sure it's not == or ===
            if re.search(r'if\s*\(\s*\w+\s*=(?!=)', line):
                bugs.append({
                    'line': i,
                    'type': 'LOGIC',
                    'severity': 'HIGH',
                    'message': "Assignment in if condition — likely a bug (should be comparison)",
                    'suggestion': "Use === instead of = for comparison"
                })

        
        # BUG 4: Using 'var' instead of let/const
        
        for i, line in enumerate(clean_lines, 1):
            if re.search(r'\bvar\s+\w+', line):
                bugs.append({
                    'line': i,
                    'type': 'STYLE',
                    'severity': 'LOW',
                    'message': "Using 'var' instead of let/const",
                    'suggestion': "Use 'const' for values that don't change, 'let' for others"
                })

       
        # BUG 5: == instead of === (loose equality)
     
        for i, line in enumerate(clean_lines, 1):
            # Find == but not === or !==
            if re.search(r'(?<![=!])==(?!=)', line):
                bugs.append({
                    'line': i,
                    'type': 'STYLE',
                    'severity': 'MEDIUM',
                    'message': "Loose equality (==) used — may cause type coercion bugs",
                    'suggestion': "Use === (strict equality) instead of =="
                })

        
        # BUG 6: console.log left in production code
        
        for i, line in enumerate(clean_lines, 1):
            if re.search(r'console\.(log|debug|info)\s*\(', line):
                bugs.append({
                    'line': i,
                    'type': 'STYLE',
                    'severity': 'LOW',
                    'message': "console.log/debug/info found — should be removed in production",
                    'suggestion': "Remove console statements or use a proper logging library"
                })

        
        # Remove duplicates (same line + same type)
       
        unique_bugs = []
        seen = set()
        for bug in bugs:
            key = (bug['line'], bug.get('type', ''), bug.get('message', ''))
            if key not in seen:
                seen.add(key)
                unique_bugs.append(bug)

        return unique_bugs