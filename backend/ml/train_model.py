import pandas as pd
import numpy as np
import os
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


def generate_training_data(n_samples=10000):
    np.random.seed(42)

    data = []

    for _ in range(n_samples):

        loc = np.random.randint(5, 800)

        functions = np.random.randint(0, max(1, loc // 20))
        classes = np.random.randint(0, max(1, loc // 100))
        loops = np.random.randint(0, max(1, loc // 30))
        conditionals = np.random.randint(0, max(1, loc // 25))
        comments = np.random.randint(0, max(1, loc // 10))
        imports = np.random.randint(0, min(20, loc // 40))

        language = np.random.choice(
            ["python", "javascript", "java", "cpp", "csharp"]
        )

        # Bug probability logic
        bug_score = (
            (loc / 800) * 0.30 +
            (loops / 20) * 0.25 +
            (conditionals / 30) * 0.25 +
            (1 - min(comments / max(1, loc), 0.5)) * 0.20
        )

        bug_score += np.random.normal(0, 0.1)

        has_bug = 1 if bug_score > 0.4 else 0

        data.append([
            loc,
            functions,
            classes,
            loops,
            conditionals,
            comments,
            imports,
            language,
            has_bug
        ])

    columns = [
        "lines_of_code",
        "functions",
        "classes",
        "loops",
        "conditionals",
        "comments",
        "imports",
        "language",
        "has_bug"
    ]

    df = pd.DataFrame(data, columns=columns)

    return df


def prepare_features(df):

    # One-hot encoding for language
    df = pd.get_dummies(df, columns=["language"], prefix="lang")

    feature_columns = [
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

    X = df[feature_columns]
    y = df["has_bug"]

    return X, y


def train_models():

    print("📊 Generating training dataset...")

    df = generate_training_data(10000)

    X, y = prepare_features(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    print("🤖 Training Random Forest model...")

    rf = RandomForestClassifier(
        n_estimators=120,
        max_depth=12,
        random_state=42
    )

    rf.fit(X_train, y_train)

    print("📈 Training Logistic Regression model...")

    lr = LogisticRegression(
        max_iter=1000,
        random_state=42
    )

    lr.fit(X_train, y_train)

    # Accuracy evaluation
    rf_pred = rf.predict(X_test)
    lr_pred = lr.predict(X_test)

    rf_acc = accuracy_score(y_test, rf_pred)
    lr_acc = accuracy_score(y_test, lr_pred)

    print(f"✅ Random Forest Accuracy : {rf_acc:.3f}")
    print(f"✅ Logistic Regression Accuracy : {lr_acc:.3f}")

    # Save models
    os.makedirs("models", exist_ok=True)

    joblib.dump(rf, "models/random_forest.pkl")
    joblib.dump(lr, "models/logistic_regression.pkl")

    print("💾 Models saved successfully")

    return rf, lr


if __name__ == "__main__":
    train_models()