from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import numpy as np
import joblib
import traceback
from analyzers.python_analyzer import PythonAnalyzer
from analyzers.javascript_analyzer import JavaScriptAnalyzer
from analyzers.java_analyzer import JavaAnalyzer
from analyzers.cpp_analyzer import CppAnalyzer
from analyzers.csharp_analyzer import CSharpAnalyzer
from ml.feature_extractor import FeatureExtractor

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# Initialize analyzers
analyzers = {
    'python': PythonAnalyzer(),
    'javascript': JavaScriptAnalyzer(),
    'java': JavaAnalyzer(),
    'cpp': CppAnalyzer(),
    'csharp': CSharpAnalyzer()
}

# Load ML models
model_dir = 'ml/models'
rf_model = None
lr_model = None
feature_extractor = FeatureExtractor()

try:
    if os.path.exists(os.path.join(model_dir, 'random_forest.pkl')):
        rf_model = joblib.load(os.path.join(model_dir, 'random_forest.pkl'))
    if os.path.exists(os.path.join(model_dir, 'logistic_regression.pkl')):
        lr_model = joblib.load(os.path.join(model_dir, 'logistic_regression.pkl'))
    print("✅ Models loaded")
except Exception as e:
    print(f"⚠️ Model loading failed: {e}")

def detect_language(code, filename):
    if filename:
        ext = filename.split('.')[-1].lower()
        lang_map = {'py': 'python', 'js': 'javascript', 'java': 'java',
                   'cpp': 'cpp', 'cxx': 'cpp', 'cc': 'cpp', 'cs': 'csharp'}
        if ext in lang_map:
            return lang_map[ext]
    
    code_lower = code.lower()
    if 'def ' in code or 'import ' in code:
        return 'python'
    elif 'function(' in code or 'console.log' in code:
        return 'javascript'
    elif 'public class' in code or 'system.out' in code_lower:
        return 'java'
    elif '#include' in code or 'cout <<' in code:
        return 'cpp'
    elif 'namespace' in code or 'console.writeline' in code_lower:
        return 'csharp'
    return 'python'

def calculate_quality_score(metrics, bugs):
    """Calculate accurate quality score"""
    if len(bugs) == 0:
        return 98
    
    score = 100
    for bug in bugs:
        severity = bug.get('severity', 'MEDIUM')
        if severity == 'CRITICAL':
            score -= 25
        elif severity == 'HIGH':
            score -= 18
        elif severity == 'MEDIUM':
            score -= 12
        elif severity == 'LOW':
            score -= 6
    
    return max(0, min(100, int(score)))

def calculate_bug_probability(metrics, bugs):
    """Calculate accurate bug probability based on actual bugs"""
    bug_count = len(bugs)
    
    if bug_count == 0:
        return 0
    elif bug_count == 1:
        return 25
    elif bug_count == 2:
        return 50
    elif bug_count == 3:
        return 70
    elif bug_count == 4:
        return 82
    else:
        return 90

def get_grade(score):
    if score >= 90: return 'A'
    elif score >= 75: return 'B'
    elif score >= 60: return 'C'
    elif score >= 40: return 'D'
    else: return 'F'

@app.route('/')
def serve_frontend():
    return send_from_directory('../frontend', 'index.html')

@app.route('/css/<path:path>')
def serve_css(path):
    return send_from_directory('../frontend/css', path)

@app.route('/js/<path:path>')
def serve_js(path):
    return send_from_directory('../frontend/js', path)

@app.route('/analyze', methods=['POST'])
def analyze_code():
    try:
        data = request.json
        code = data.get('code', '')
        filename = data.get('filename', '')
        language = data.get('language', 'auto')
        
        if not code.strip():
            return jsonify({'error': 'No code provided'}), 400
        
        if language == 'auto':
            language = detect_language(code, filename)
        
        analyzer = analyzers.get(language)
        if not analyzer:
            return jsonify({'error': f'Language {language} not supported'}), 400
        
        metrics = analyzer.extract_metrics(code)
        detected_bugs = analyzer.detect_bugs(code, metrics)
        
        # Calculate using actual bugs only (no filtering needed now)
        bug_probability = calculate_bug_probability(metrics, detected_bugs)
        quality_score = calculate_quality_score(metrics, detected_bugs)
        quality_grade = get_grade(quality_score)
        
        if bug_probability >= 70:
            risk_level = "HIGH RISK"
        elif bug_probability >= 40:
            risk_level = "MEDIUM RISK"
        else:
            risk_level = "LOW RISK"
        
        bug_counts = {
            'critical': sum(1 for b in detected_bugs if b.get('severity') == 'CRITICAL'),
            'high': sum(1 for b in detected_bugs if b.get('severity') == 'HIGH'),
            'medium': sum(1 for b in detected_bugs if b.get('severity') == 'MEDIUM'),
            'low': sum(1 for b in detected_bugs if b.get('severity') == 'LOW')
        }
        
             
        # REAL BUG-SPECIFIC SUGGESTIONS 
     
        suggestions = []
        
        if detected_bugs:
            # Loop through each bug and give specific solution
            for bug in detected_bugs:
                msg = bug.get('message', '').lower()
                line_num = bug.get('line', '?')
                bug_type = bug.get('type', '')
                
                # ===== SPECIFIC SUGGESTIONS FOR EACH BUG TYPE =====
                
                # 1. Using namespace std
                if 'using namespace std' in msg or 'namespace' in msg:
                    suggestions.append(f"Line {line_num}: Replace 'using namespace std' with 'std::' prefix")
                    suggestions.append(f"  → Change: cout << x;  →  std::cout << x;")
                    suggestions.append(f"  → Change: cin >> x;   →  std::cin >> x;")
                
                # 2. Missing return statement
                elif 'return' in msg and ('no return' in msg or 'missing return' in msg):
                    func_name = 'function'
                    if 'main' in msg:
                        suggestions.append(f"Line {line_num}: Add 'return 0;' at end of main function")
                        suggestions.append(f"  → int main() {{ ... return 0; }}")
                    else:
                        suggestions.append(f"Line {line_num}: Add return statement with appropriate value")
                        suggestions.append(f"  → Example: return value; or return result;")
                
                # 3. Undefined variable
                elif 'undefined' in msg or 'not defined' in msg:
                    # Extract variable name from message
                    import re
                    var_match = re.search(r"'([^']+)'", msg)
                    var_name = var_match.group(1) if var_match else 'variable'
                    
                    suggestions.append(f"Line {line_num}: Variable '{var_name}' is not defined")
                    suggestions.append(f"  → Declare it before use: {var_name} = value")
                    if language == 'cpp' or language == 'java':
                        suggestions.append(f"  → Example: int {var_name} = 0;")
                    elif language == 'javascript':
                        suggestions.append(f"  → Example: let {var_name} = 0; or const {var_name} = value;")
                    else:
                        suggestions.append(f"  → Example: {var_name} = value")
                
                # 4. Off-by-one / Array index error
                elif 'index' in msg or 'off-by-one' in msg or 'bounds' in msg:
                    suggestions.append(f"Line {line_num}: Array index out of bounds risk")
                    suggestions.append(f"  → Change: for(i = 0; i <= length; i++)")
                    suggestions.append(f"  → To:      for(i = 0; i < length; i++)")
                    suggestions.append(f"  → Array indices go from 0 to length-1")
                
                # 5. Infinite loop
                elif 'infinite loop' in msg or 'i--' in msg:
                    suggestions.append(f"Line {line_num}: Infinite loop detected")
                    suggestions.append(f"  → Change: for(i = 0; i < 10; i--)  (i-- causes infinite loop)")
                    suggestions.append(f"  → To:      for(i = 0; i < 10; i++)")
                    if 'while' in msg:
                        suggestions.append(f"  → Add increment: i++ inside while loop")
                
                # 6. Division by zero
                elif 'division by zero' in msg:
                    suggestions.append(f"Line {line_num}: Division by zero error")
                    suggestions.append(f"  → Add check before division:")
                    suggestions.append(f"  → if(denominator != 0) {{ result = numerator / denominator; }}")
                    suggestions.append(f"  → else {{ handle error }}")
                
                # 7. Bare except / Empty catch
                elif 'bare except' in msg or 'empty catch' in msg:
                    suggestions.append(f"Line {line_num}: Empty exception handler")
                    suggestions.append(f"  → Specify exception type and handle it:")
                    if language == 'python':
                        suggestions.append(f"  → except Exception as e: print(f'Error: {{e}}')")
                    else:
                        suggestions.append(f"  → catch(Exception e) {{ Console.WriteLine(e.Message); }}")
                
                # 8. var usage in JavaScript
                elif 'var' in msg and 'instead' in msg:
                    suggestions.append(f"Line {line_num}: Using 'var' instead of 'let' or 'const'")
                    suggestions.append(f"  → Change: var x = 10;")
                    suggestions.append(f"  → To:      let x = 10;   (if value changes)")
                    suggestions.append(f"  → Or:      const x = 10; (if value is constant)")
                
                # 9. Memory leak (C++)
                elif 'memory' in msg or 'leak' in msg:
                    suggestions.append(f"Line {line_num}: Potential memory leak")
                    suggestions.append(f"  → Add delete for every new:")
                    suggestions.append(f"  → int* ptr = new int[10]; ... delete[] ptr;")
                    suggestions.append(f"  → Or use smart pointers: unique_ptr<int[]> ptr(new int[10]);")
                
                # 10. Division by zero (generic)
                elif 'division' in msg:
                    suggestions.append(f"Line {line_num}: Division operation may cause error")
                    suggestions.append(f"  → Check if divisor is zero before division")
                    suggestions.append(f"  → Use try-catch for exception handling")
                
                # 11. Syntax error
                elif 'syntax' in msg:
                    suggestions.append(f"Line {line_num}: Syntax error")
                    if ':' in msg:
                        suggestions.append(f"  → Check for missing colon ':' after if/for/def")
                    elif ';' in msg:
                        suggestions.append(f"  → Check for missing semicolon ';' at end of statement")
                    elif '(' in msg or ')' in msg:
                        suggestions.append(f"  → Check for mismatched parentheses '(' and ')'")
                    elif '{' in msg or '}' in msg:
                        suggestions.append(f"  → Check for mismatched braces '{{' and '}}'")
                
                # 12. Generic bug - show original suggestion
                else:
                    suggestions.append(f"Line {line_num}: {bug.get('message', 'Issue detected')}")
                    suggestions.append(f"  → {bug.get('suggestion', 'Fix this issue')}")
        
        else:
            suggestions.append("No bugs detected! Your code looks clean.")
            suggestions.append("Tip: Add comments for complex logic")
        
        
        # Remove duplicates but keep in order
        unique_suggestions = []
        seen = set()
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique_suggestions.append(s)
        
        suggestions = unique_suggestions[:10]  # Max 10 suggestions
        
        response = {
            'success': True,
            'language': language,
            'summary': {
                'total_bugs': len(detected_bugs),
                'bug_probability': bug_probability,
                'risk_level': risk_level,
                'quality_score': quality_score,
                'quality_grade': quality_grade,
                'bug_counts': bug_counts
            },
            'bugs': detected_bugs[:30],
            'metrics': metrics,
            'suggestions': suggestions
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))