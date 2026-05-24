import numpy as np

class FeatureExtractor:
    def __init__(self):
        # Fixed feature order for ML model
        self.feature_names = [
            "lines_of_code",
            "functions",
            "classes",
            "loops",
            "conditionals",
            "comments",
            "imports",
            "lang_python",
            "lang_javascript",
            "lang_java",
            "lang_cpp",
            "lang_csharp"
        ]

    def extract(self, metrics, language):
        """
        Convert code metrics into ML feature vector
        """

        # Normalize numeric metrics
        loc = min(metrics.get("lines_of_code", 0) / 1000, 1.0)
        functions = min(metrics.get("functions", 0) / 50, 1.0)
        classes = min(metrics.get("classes", 0) / 20, 1.0)
        loops = min(metrics.get("loops", 0) / 30, 1.0)
        conditionals = min(metrics.get("conditionals", 0) / 40, 1.0)
        comments = min(metrics.get("comments", 0) / 200, 1.0)
        imports = min(metrics.get("imports", 0) / 30, 1.0)

        numeric_features = [
            loc,
            functions,
            classes,
            loops,
            conditionals,
            comments,
            imports
        ]

        # Language encoding
        languages = ["python", "javascript", "java", "cpp", "csharp"]
        lang_features = [1 if language == lang else 0 for lang in languages]

        features = numeric_features + lang_features

        # Convert to numpy array (required by sklearn)
        return np.array(features).reshape(1, -1)