#!/usr/bin/env python3
"""
Training script for the handwriting recognition model.

This script handles training and evaluation of the stroke recognition model.
"""

import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple, Optional
import argparse
import glob
from pathlib import Path
import time

# Import custom modules
from model import RemarkableLSTM
from dataset import create_character_dataset, create_synthetic_dataset


def train(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    num_epochs: int = 50,
    learning_rate: float = 0.001,
    weight_decay: float = 1e-5,
    patience: int = 5,
    model_dir: str = "checkpoints",
    device: str = "cuda" if torch.cuda.is_available() else "cpu",
) -> nn.Module:
    """
    Train the model.

    Args:
        model: Model to train
        train_loader: DataLoader for training data
        val_loader: DataLoader for validation data
        num_epochs: Number of epochs to train for
        learning_rate: Learning rate for optimizer
        weight_decay: Weight decay for optimizer
        patience: Number of epochs to wait for improvement before early stopping
        model_dir: Directory to save model checkpoints
        device: Device to train on ('cuda' or 'cpu')

    Returns:
        Trained model
    """
    # Create model directory
    os.makedirs(model_dir, exist_ok=True)

    # Move model to device
    model = model.to(device)

    # Define loss function and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(
        model.parameters(), lr=learning_rate, weight_decay=weight_decay
    )

    # Learning rate scheduler
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, "min", patience=3, factor=0.5
    )
    print("Created learning rate scheduler")

    # Track metrics
    train_losses = []
    val_losses = []
    val_accuracies = []

    # For early stopping
    best_val_loss = float("inf")
    best_epoch = 0
    best_model_path = os.path.join(model_dir, "best_model.pt")

    # Training loop
    start_time = time.time()
    for epoch in range(num_epochs):
        # Training
        model.train()
        train_loss = 0.0

        for batch_x, batch_y in train_loader:
            # Move data to device
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)

            # Zero gradients
            optimizer.zero_grad()

            # Forward pass
            outputs = model(batch_x)

            # Calculate loss
            loss = criterion(outputs, batch_y)

            # Backward pass
            loss.backward()

            # Update weights
            optimizer.step()

            # Track loss
            train_loss += loss.item()

        # Average training loss
        avg_train_loss = train_loss / len(train_loader)
        train_losses.append(avg_train_loss)

        # Validation
        model.eval()
        val_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                # Move data to device
                batch_x = batch_x.to(device)
                batch_y = batch_y.to(device)

                # Forward pass
                outputs = model(batch_x)

                # Calculate loss
                loss = criterion(outputs, batch_y)
                val_loss += loss.item()

                # Calculate accuracy
                _, predicted = torch.max(outputs, 1)
                total += batch_y.size(0)
                correct += (predicted == batch_y).sum().item()

        # Average validation loss and accuracy
        avg_val_loss = val_loss / len(val_loader)
        val_losses.append(avg_val_loss)

        val_accuracy = 100.0 * correct / total
        val_accuracies.append(val_accuracy)

        # Update learning rate
        scheduler.step(avg_val_loss)

        # Print progress
        elapsed_time = time.time() - start_time
        print(
            f"Epoch {epoch + 1}/{num_epochs} | "
            f"Train Loss: {avg_train_loss:.4f} | "
            f"Val Loss: {avg_val_loss:.4f} | "
            f"Val Acc: {val_accuracy:.2f}% | "
            f"Time: {elapsed_time:.1f}s"
        )

        # Save best model
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_epoch = epoch

            # Save model
            torch.save(model.state_dict(), best_model_path)
            print(f"Saved best model (Val Loss: {best_val_loss:.4f})")

        # Early stopping
        if epoch - best_epoch >= patience:
            print(f"Early stopping (no improvement for {patience} epochs)")
            break

    # Load best model
    model.load_state_dict(torch.load(best_model_path))

    # Save training history
    history = {
        "train_loss": train_losses,
        "val_loss": val_losses,
        "val_accuracy": val_accuracies,
    }

    with open(os.path.join(model_dir, "training_history.json"), "w") as f:
        json.dump(history, f, indent=2)

    # Plot training history
    plt.figure(figsize=(12, 5))

    # Plot loss
    plt.subplot(1, 2, 1)
    plt.plot(train_losses, label="Train Loss")
    plt.plot(val_losses, label="Val Loss")
    plt.title("Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend()

    # Plot accuracy
    plt.subplot(1, 2, 2)
    plt.plot(val_accuracies, label="Val Accuracy")
    plt.title("Validation Accuracy")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy (%)")
    plt.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(model_dir, "training_history.png"))

    return model


def evaluate(
    model: nn.Module,
    test_loader: DataLoader,
    device: str = "cuda" if torch.cuda.is_available() else "cpu",
) -> Tuple[float, float]:
    """
    Evaluate the model on test data.

    Args:
        model: Model to evaluate
        test_loader: DataLoader for test data
        device: Device to evaluate on ('cuda' or 'cpu')

    Returns:
        Tuple of (test loss, test accuracy)
    """
    # Move model to device
    model = model.to(device)
    model.eval()

    # Define loss function
    criterion = nn.CrossEntropyLoss()

    # Track metrics
    test_loss = 0.0
    correct = 0
    total = 0

    # Class-wise accuracy
    class_correct = {}
    class_total = {}

    with torch.no_grad():
        for batch_x, batch_y in test_loader:
            # Move data to device
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)

            # Forward pass
            outputs = model(batch_x)

            # Calculate loss
            loss = criterion(outputs, batch_y)
            test_loss += loss.item()

            # Calculate accuracy
            _, predicted = torch.max(outputs, 1)
            total += batch_y.size(0)
            correct += (predicted == batch_y).sum().item()

            # Track class-wise accuracy
            for i in range(len(batch_y)):
                label = batch_y[i].item()
                pred = predicted[i].item()

                if label not in class_total:
                    class_total[label] = 0
                    class_correct[label] = 0

                class_total[label] += 1
                if label == pred:
                    class_correct[label] += 1

    # Average test loss and accuracy
    avg_test_loss = test_loss / len(test_loader)
    test_accuracy = 100.0 * correct / total

    # Print results
    print(f"Test Loss: {avg_test_loss:.4f} | Test Accuracy: {test_accuracy:.2f}%")

    # Print class-wise accuracy
    print("\nClass-wise Accuracy:")
    for label in sorted(class_total.keys()):
        accuracy = 100.0 * class_correct[label] / class_total[label]
        char = chr(label + 32) if 0 <= label <= 94 else f"Class {label}"
        print(f"{char}: {accuracy:.2f}% ({class_correct[label]}/{class_total[label]})")

    return avg_test_loss, test_accuracy


def main():
    """Main function."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Train handwriting recognition model")

    # Data arguments
    parser.add_argument("--data-dir", type=str, default="data", help="Data directory")
    parser.add_argument(
        "--synthetic", action="store_true", help="Create and use synthetic data"
    )
    parser.add_argument(
        "--num-synthetic", type=int, default=5000, help="Number of synthetic samples"
    )

    # Model arguments
    parser.add_argument(
        "--hidden-dim", type=int, default=128, help="Hidden dimension of LSTM"
    )
    parser.add_argument("--n-layers", type=int, default=2, help="Number of LSTM layers")
    parser.add_argument(
        "--bidirectional", action="store_true", help="Use bidirectional LSTM"
    )
    parser.add_argument(
        "--dropout", type=float, default=0.2, help="Dropout probability"
    )

    # Training arguments
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size")
    parser.add_argument("--epochs", type=int, default=50, help="Number of epochs")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    parser.add_argument("--weight-decay", type=float, default=1e-5, help="Weight decay")
    parser.add_argument(
        "--patience", type=int, default=5, help="Patience for early stopping"
    )

    # Output arguments
    parser.add_argument(
        "--model-dir", type=str, default="checkpoints", help="Model directory"
    )

    # Device arguments
    parser.add_argument("--cpu", action="store_true", help="Force CPU usage")

    # Parse arguments
    args = parser.parse_args()

    # Set device
    device = "cpu" if args.cpu else ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Create data directory if it doesn't exist
    os.makedirs(args.data_dir, exist_ok=True)

    # Create synthetic data if requested
    if args.synthetic:
        synthetic_dir = os.path.join(args.data_dir, "synthetic")
        create_synthetic_dataset(synthetic_dir, args.num_synthetic)

        # Get files
        stroke_files = glob.glob(os.path.join(synthetic_dir, "synthetic_*.json"))
        label_file = os.path.join(synthetic_dir, "labels.json")
    else:
        # Get files from data directory
        stroke_files = []
        for ext in [".json", ".rm", ".content"]:
            stroke_files.extend(glob.glob(os.path.join(args.data_dir, f"*{ext}")))

        label_file = os.path.join(args.data_dir, "labels.json")

        # Check if label file exists
        if not os.path.exists(label_file):
            print(f"Label file not found: {label_file}")
            print("Creating empty label file...")
            with open(label_file, "w") as f:
                json.dump({}, f)

    # Create dataset
    train_loader, val_loader, test_loader = create_character_dataset(
        stroke_files=stroke_files,
        label_file=label_file,
        batch_size=args.batch_size,
        max_length=100,
        test_split=0.2,
        val_split=0.1,
        shuffle=True,
        num_workers=0,
    )

    # Create model
    model = RemarkableLSTM(
        n_input_features=5,
        lstm_hidden_dim=args.hidden_dim,
        lstm_n_layers=args.n_layers,
        fc_hidden_dim=args.hidden_dim,
        num_classes=95,  # ASCII printable chars
        bidirectional=args.bidirectional,
        dropout=args.dropout,
    )

    # Print model summary
    print(model)

    # Train model
    model = train(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        num_epochs=args.epochs,
        learning_rate=args.lr,
        weight_decay=args.weight_decay,
        patience=args.patience,
        model_dir=args.model_dir,
        device=device,
    )

    # Evaluate model
    evaluate(model, test_loader, device)


if __name__ == "__main__":
    main()
