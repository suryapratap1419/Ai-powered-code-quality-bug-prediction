import re
from .base_analyzer import BaseAnalyzer


class CSharpAnalyzer(BaseAnalyzer):
    """C# Code Analyzer"""

    def extract_metrics(self, code):
        metrics = {
            "lines_of_code": self.count_lines(code),
            "functions": 0,
            "classes": 0,
            "loops": 0,
            "conditionals": 0,
            "comments": 0,
            "imports": 0
        }

        comment_symbols = {
            "single": ["//"],
            "multi_start": "/*",
            "multi_end": "*/"
        }

        # Count comments
        metrics["comments"] = self.count_comments(code, comment_symbols)

        # Detect methods
        method_pattern = r'(public|private|protected|internal)?\s*\w+\s+(\w+)\s*\([^)]*\)\s*\{'
        metrics["functions"] = len(re.findall(method_pattern, code))

        # Detect classes
        class_pattern = r'\bclass\s+(\w+)'
        metrics["classes"] = len(re.findall(class_pattern, code))

        # Detect loops
        loop_pattern = r'\b(for|foreach|while|do)\s*\('
        metrics["loops"] = len(re.findall(loop_pattern, code))

        # Detect conditionals
        conditional_pattern = r'\b(if|else\s+if|switch)\s*\('
        metrics["conditionals"] = len(re.findall(conditional_pattern, code))

        # Detect using imports
        import_pattern = r'^\s*using\s+'
        metrics["imports"] = len(re.findall(import_pattern, code, re.MULTILINE))

        return metrics

    def detect_bugs(self, code, metrics):
        bugs = []
        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Skip comments
            if stripped.startswith("//") or stripped.startswith("*"):
                continue

            # Debug statements
            if "Console.WriteLine" in stripped and metrics["lines_of_code"] > 30:
                bugs.append({
                    "line": i,
                    "type": "DEBUG",
                    "severity": "LOW",
                    "message": "Console.WriteLine found in production code",
                    "suggestion": "Remove debug statement or use proper logging (ILogger)"
                })

            # Possible infinite loop
            if "for" in stripped and "i--" in stripped:
                bugs.append({
                    "line": i,
                    "type": "LOGIC",
                    "severity": "HIGH",
                    "message": "Possible infinite loop using i--",
                    "suggestion": "Use i++ or check loop condition"
                })

            # Hardcoded credentials
            if re.search(r'password\s*=', stripped, re.IGNORECASE):
                bugs.append({
                    "line": i,
                    "type": "SECURITY",
                    "severity": "HIGH",
                    "message": "Hardcoded password detected",
                    "suggestion": "Store credentials in environment variables or config files"
                })

            # Empty catch block
            if "catch" in stripped and "{" in stripped:
                next_index = i
                if next_index < len(lines):
                    next_line = lines[next_index].strip()
                    if next_line == "}":
                        bugs.append({
                            "line": i,
                            "type": "LOGIC",
                            "severity": "MEDIUM",
                            "message": "Empty catch block detected",
                            "suggestion": "Handle exception or log error"
                        })

        return bugs