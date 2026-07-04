#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import LinearSVC, SVC
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report
)

from scipy.sparse import hstack, csr_matrix


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VOICE_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(VOICE_DIR, "data")
MODEL_DIR = os.path.join(VOICE_DIR, "models")

DEFAULT_TRAIN = os.path.join(DATA_DIR, "train_commands.csv")
DEFAULT_TEST = os.path.join(DATA_DIR, "test_commands.csv")
DEFAULT_OUT = os.path.join(MODEL_DIR, "mejor_modelo.joblib")

REQUIRED_COLS = {"command", "intention", "start_goal", "end_goal"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Entrenador de clasificadores de comandos de voz"
    )
    parser.add_argument("--train", default=DEFAULT_TRAIN)
    parser.add_argument("--test", default=DEFAULT_TEST)
    parser.add_argument("--out", default=DEFAULT_OUT)
    return parser.parse_args()


def load_csv(path):
    if not os.path.exists(path):
        sys.exit(f"[ERROR] Archivo no encontrado: {path}")

    df = pd.read_csv(path)

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        sys.exit(f"[ERROR] Columnas faltantes en {path}: {missing}")

    df["command"] = df["command"].astype(str).str.lower().str.strip()
    df["start_goal"] = pd.to_numeric(
        df["start_goal"], errors="coerce"
    ).fillna(0).astype(int)
    df["end_goal"] = pd.to_numeric(
        df["end_goal"], errors="coerce"
    ).fillna(0).astype(int)

    return df


def build_features(df):
    X_text = df["command"]
    X_num = df[["start_goal", "end_goal"]].values
    y = df["intention"]
    return X_text, X_num, y


def build_X(tfidf, X_text, X_num, fit=False):
    if fit:
        T = tfidf.fit_transform(X_text)
    else:
        T = tfidf.transform(X_text)

    N = csr_matrix(np.asarray(X_num).astype(float))
    return hstack([T, N])


def compute_metrics(y_true, y_pred, name):
    return {
        "model": name,
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(
            y_true, y_pred, average="weighted", zero_division=0
        ),
        "recall": recall_score(
            y_true, y_pred, average="weighted", zero_division=0
        ),
        "f1": f1_score(
            y_true, y_pred, average="weighted", zero_division=0
        ),
    }


SEP = "=" * 65


def section(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")


def main():
    args = parse_args()

    section("CARGA DE DATOS")

    df_train = load_csv(args.train)
    df_test = load_csv(args.test)

    print(f"  Train : {len(df_train):>4} muestras  →  {args.train}")
    print(f"  Test  : {len(df_test):>4} muestras  →  {args.test}")

    clases = sorted(df_train["intention"].unique())

    print(f"\n  Clases ({len(clases)}): {clases}")
    print("\n  Distribución en train:")
    print(df_train["intention"].value_counts().to_string(header=False))

    Xtr_text, Xtr_num, ytr = build_features(df_train)
    Xte_text, Xte_num, yte = build_features(df_test)

    modelos = {
        "Arbol de Decision": {
            "clf": DecisionTreeClassifier(max_depth=None, random_state=42),
            "tfidf_params": None,
        },
        "Naive Bayes": {
            "clf": MultinomialNB(alpha=0.5),
            "tfidf_params": {"sublinear_tf": False},
        },
        "KNN (k=5)": {
            "clf": KNeighborsClassifier(n_neighbors=5, metric="cosine"),
            "tfidf_params": None,
        },
        "SVM Lineal": {
            "clf": LinearSVC(C=1.0, max_iter=5000, random_state=42),
            "tfidf_params": None,
        },
        "SVM RBF": {
            "clf": SVC(C=10.0, kernel="rbf", gamma="scale", random_state=42),
            "tfidf_params": None,
        },
    }

    section("ENTRENAMIENTO Y EVALUACION")

    resultados = []

    for nombre, cfg in modelos.items():
        print(f"\n  ▶  {nombre}")

        tfidf_base = {
            "analyzer": "word",
            "ngram_range": (1, 2),
            "sublinear_tf": True,
            "min_df": 1,
        }

        if cfg["tfidf_params"]:
            tfidf_base.update(cfg["tfidf_params"])

        tfidf = TfidfVectorizer(**tfidf_base)
        clf = cfg["clf"]

        try:
            Xtr = build_X(tfidf, Xtr_text, Xtr_num, fit=True)
            Xte = build_X(tfidf, Xte_text, Xte_num, fit=False)

            clf.fit(Xtr, ytr.values)
            y_pred = clf.predict(Xte)

            metricas = compute_metrics(yte.values, y_pred, nombre)

            resultados.append({
                **metricas,
                "tfidf": tfidf,
                "clf": clf,
            })

            print(f"     Accuracy  : {metricas['accuracy']:.4f}")
            print(f"     Precision : {metricas['precision']:.4f}")
            print(f"     Recall    : {metricas['recall']:.4f}")
            print(f"     F1-score  : {metricas['f1']:.4f}")

            print("\n     Reporte detallado:")

            reporte = classification_report(
                yte.values,
                y_pred,
                labels=clases,
                target_names=clases,
                zero_division=0,
            )

            for line in reporte.split("\n"):
                print(f"       {line}")

        except Exception as e:
            print(f"     [WARN] No se pudo entrenar {nombre}: {e}")

    if not resultados:
        sys.exit("[ERROR] Ningún modelo pudo entrenarse.")

    section("TABLA COMPARATIVA DE MODELOS")

    df_res = pd.DataFrame([
        {
            "model": r["model"],
            "accuracy": r["accuracy"],
            "precision": r["precision"],
            "recall": r["recall"],
            "f1": r["f1"],
        }
        for r in resultados
    ]).sort_values("f1", ascending=False).reset_index(drop=True)

    CW = 22

    print(
        f"  {'Modelo':<{CW}} "
        f"{'Accuracy':>10} "
        f"{'Precision':>10} "
        f"{'Recall':>10} "
        f"{'F1-score':>10}"
    )
    print("  " + "-" * (CW + 44))

    for i, row in df_res.iterrows():
        marca = "  ◀ MEJOR" if i == 0 else ""
        print(
            f"  {row['model']:<{CW}} "
            f"{row['accuracy']:>10.4f} "
            f"{row['precision']:>10.4f} "
            f"{row['recall']:>10.4f} "
            f"{row['f1']:>10.4f}"
            f"{marca}"
        )

    mejor_nombre = df_res.iloc[0]["model"]
    mejor_entry = next(r for r in resultados if r["model"] == mejor_nombre)
    mejor_f1 = mejor_entry["f1"]

    section("MEJOR MODELO SELECCIONADO")

    print(f"  Modelo   : {mejor_nombre}")
    print(f"  F1 (w)   : {mejor_f1:.4f}")
    print("  Criterio : F1-score ponderado (weighted)")

    section("GUARDADO DEL MODELO")

    out_path = args.out
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    payload = {
        "model_name": mejor_nombre,
        "tfidf": mejor_entry["tfidf"],
        "clf": mejor_entry["clf"],
        "classes": clases,
        "metrics": {
            "accuracy": mejor_entry["accuracy"],
            "precision": mejor_entry["precision"],
            "recall": mejor_entry["recall"],
            "f1": mejor_entry["f1"],
        },
        "feature_cols": ["command", "start_goal", "end_goal"],
        "label_col": "intention",
    }

    joblib.dump(payload, out_path)

    print(f"\n  ✔  Guardado en : {out_path}")
    print(f"     Tamaño      : {os.path.getsize(out_path) / 1024:.1f} KB")

    section("EJEMPLO DE INFERENCIA")

    payload_inf = joblib.load(out_path)
    tfidf_inf = payload_inf["tfidf"]
    clf_inf = payload_inf["clf"]

    ejemplos = [
        ("robot desplazate del objetivo uno hasta el tres", 1, 3),
        ("husky ejecuta trayectoria completa", 0, 0),
        ("activa modo 4 con recorrido ciclico", 0, 0),
        ("robot vaya al punto dos", 0, 2),
        ("repite el recorrido en bucle", 0, 0),
        ("husky completa todo el recorrido", 0, 0),
    ]

    print(f"\n  {'Comando':<56} {'Prediccion'}")
    print("  " + "-" * 70)

    for cmd, sg, eg in ejemplos:
        T = tfidf_inf.transform(pd.Series([cmd]))
        N = csr_matrix(np.array([[sg, eg]], dtype=float))
        X = hstack([T, N])
        pred = clf_inf.predict(X)[0]
        print(f"  {cmd:<56} {pred}")

    section("FIN")
    print("  Script completado exitosamente.\n")


if __name__ == "__main__":
    main()
