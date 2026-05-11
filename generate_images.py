import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

runs = [
    {
        "name": "run_001",
        "title": "Image Classification v1 - Run 001",
        "accuracy": 0.9134,
        "labels": ["Cat", "Dog"],
        "matrix": np.array([[46, 4],
                             [5, 45]])
    },
    {
        "name": "run_002",
        "title": "Image Classification v1 - Run 002",
        "accuracy": 0.8721,
        "labels": ["Cat", "Dog"],
        "matrix": np.array([[44, 6],
                             [7, 43]])
    },
    {
        "name": "run_003",
        "title": "Image Classification v1 - Run 003",
        "accuracy": 0.9450,
        "labels": ["Cat", "Dog"],
        "matrix": np.array([[48, 2],
                             [3, 47]])
    },
    {
        "name": "run_004",
        "title": "Speech Recognition v1 - Run 004",
        "accuracy": 0.8200,
        "labels": ["Correct", "Incorrect"],
        "matrix": np.array([[41, 9],
                             [9, 41]])
    },
    {
        "name": "run_005",
        "title": "Speech Recognition v1 - Run 005",
        "accuracy": 0.7600,
        "labels": ["Correct", "Incorrect"],
        "matrix": np.array([[38, 12],
                             [12, 38]])
    },
]

for run in runs:
    fig, ax = plt.subplots(figsize=(6, 5))

    sns.heatmap(
        run["matrix"],
        annot=True,
        fmt='d',
        cmap='Blues',
        xticklabels=run["labels"],
        yticklabels=run["labels"],
        linewidths=0.5,
        linecolor='gray',
        ax=ax
    )

    ax.set_title(f'{run["title"]}\nAccuracy: {run["accuracy"]:.4f}', fontsize=12, fontweight='bold', pad=12)
    ax.set_ylabel('Actual Label', fontsize=11)
    ax.set_xlabel('Predicted Label', fontsize=11)

    plt.tight_layout()
    filename = f'confusion_{run["name"]}.png'
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f'Saved: {filename}')

print('\nDone! 5 confusion matrix images generated.')
