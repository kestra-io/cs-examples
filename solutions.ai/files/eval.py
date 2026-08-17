#!/usr/bin/env python3
"""Demo: simulate an offline evaluation of a shopping-cart object detection model."""

import argparse
import json
import random
from datetime import datetime, timezone


def simulate_evaluation(model_name: str, model_version: str) -> dict:
    random.seed(f"{model_name}-{model_version}")

    classes = [
        "beverage_can", "cereal_box", "produce_bag", "milk_carton",
        "bread_loaf", "snack_bag", "canned_food", "bottle",
    ]

    per_class = {}
    for c in classes:
        ap = round(random.uniform(0.62, 0.94), 4)
        per_class[c] = {
            "AP@0.50:0.95": ap,
            "AP@0.50": round(min(ap + random.uniform(0.03, 0.09), 0.99), 4),
            "AP@0.75": round(max(ap - random.uniform(0.02, 0.06), 0.30), 4),
            "precision": round(random.uniform(0.70, 0.96), 4),
            "recall": round(random.uniform(0.65, 0.93), 4),
            "support": random.randint(180, 1200),
        }

    aps = [v["AP@0.50:0.95"] for v in per_class.values()]
    mean = lambda xs: round(sum(xs) / len(xs), 4)

    return {
        "model_name": model_name,
        "model_version": model_version,
        "task": "object_detection",
        "domain": "retail_shopping_cart",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "name": "cart_holdout_v3",
            "num_images": 4820,
            "num_annotations": 31964,
            "split": "test",
        },
        "metrics": {
            "mAP@0.50:0.95": mean(aps),
            "mAP@0.50": mean([v["AP@0.50"] for v in per_class.values()]),
            "mAP@0.75": mean([v["AP@0.75"] for v in per_class.values()]),
            "mAP_small": round(mean(aps) - random.uniform(0.08, 0.15), 4),
            "mAP_medium": round(mean(aps) + random.uniform(0.01, 0.05), 4),
            "mAP_large": round(min(mean(aps) + random.uniform(0.05, 0.10), 0.98), 4),
            "AR@1": round(random.uniform(0.40, 0.55), 4),
            "AR@10": round(random.uniform(0.60, 0.75), 4),
            "AR@100": round(random.uniform(0.70, 0.85), 4),
            "mean_precision": mean([v["precision"] for v in per_class.values()]),
            "mean_recall": mean([v["recall"] for v in per_class.values()]),
            "mean_f1": mean([
                round(2 * v["precision"] * v["recall"] / (v["precision"] + v["recall"]), 4)
                for v in per_class.values()
            ]),
        },
        "per_class": per_class,
        "confusion": {
            "false_positives": random.randint(300, 900),
            "false_negatives": random.randint(250, 800),
            "iou_threshold": 0.50,
            "confidence_threshold": 0.25,
        },
        "inference": {
            "avg_latency_ms": round(random.uniform(12.0, 35.0), 2),
            "p95_latency_ms": round(random.uniform(35.0, 70.0), 2),
            "fps": round(random.uniform(28.0, 80.0), 1),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate an offline ML model evaluation.")
    parser.add_argument("--modelName", required=True, help="Name of the model.")
    parser.add_argument("--modelVersion", required=True, help="Version of the model.")
    args = parser.parse_args()

    print(f"Model Name:    {args.modelName}")
    print(f"Model Version: {args.modelVersion}")
    print("-" * 40)

    results = simulate_evaluation(args.modelName, args.modelVersion)
    output_path = "modelReport.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
 
    print(f"Evaluation report written to {output_path}")



if __name__ == "__main__":
    main()