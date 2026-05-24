from abc import ABC, abstractmethod


class BaseAnalyzer(ABC):
    """
    Base class for all language analyzers
    """

    @abstractmethod
    def extract_metrics(self, code):
        pass

    @abstractmethod
    def detect_bugs(self, code, metrics):
        pass

    def count_lines(self, code):
        """
        Count total lines of code (including blank lines)
        """
        if not code:
            return 0
        return len(code.splitlines())

    def count_comments(self, code, comment_symbols):
        """
        Count single-line and multi-line comments
        """
        if not code:
            return 0

        lines = code.splitlines()

        count = 0
        in_multiline = False

        single_symbols = comment_symbols.get("single", [])
        multi_start = comment_symbols.get("multi_start")
        multi_end = comment_symbols.get("multi_end")

        for line in lines:

            stripped = line.strip()

            if not stripped:
                continue

            # Check multiline start
            if multi_start and multi_start in stripped:
                in_multiline = True
                count += 1
                continue

            # Check multiline end
            if multi_end and multi_end in stripped:
                in_multiline = False
                count += 1
                continue

            # Inside multiline
            if in_multiline:
                count += 1
                continue

            # Single-line comments
            for symbol in single_symbols:
                if stripped.startswith(symbol):
                    count += 1
                    break

        return count