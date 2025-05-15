import os
import numpy as np
import torch
import torch.nn as nn
from typing import List, Dict, Tuple, Optional, Union


class RemarkableLSTM(nn.Module):
    """
    LSTM-based neural network for handwriting recognition from reMarkable strokes.
    Adapted from deep-scribe's approach but customized for reMarkable data format.
    """

    def __init__(
        self,
        n_input_features: int = 5,  # x, y, pressure, dx, dy
        lstm_hidden_dim: int = 128,
        lstm_n_layers: int = 2,  # Changed from 3 to 2 to match trained model
        fc_hidden_dim: int = 128,
        num_classes: int = 95,  # Changed from 96 to 95 to match trained model
        bidirectional: bool = True,
        dropout: float = 0.2,
    ):
        """
        Initialize the LSTM network for handwriting recognition.

        Args:
            n_input_features: Number of features per point (x, y, pressure, dx, dy)
            lstm_hidden_dim: Dimension of LSTM hidden state
            lstm_n_layers: Number of LSTM layers
            fc_hidden_dim: Number of neurons in hidden fully connected layer
            num_classes: Number of output classes (characters)
            bidirectional: Whether to use bidirectional LSTM
            dropout: Dropout probability for regularization
        """
        super(RemarkableLSTM, self).__init__()

        self.n_input_features = n_input_features
        self.lstm_hidden_dim = lstm_hidden_dim
        self.lstm_n_layers = lstm_n_layers
        self.num_dir = 2 if bidirectional else 1
        self.dropout = dropout

        # LSTM layer
        self.lstm = nn.LSTM(
            input_size=n_input_features,
            hidden_size=lstm_hidden_dim,
            num_layers=lstm_n_layers,
            batch_first=True,
            bidirectional=bidirectional,
            dropout=dropout if lstm_n_layers > 1 else 0,
        )

        # Fully connected layers
        lstm_output_dim = lstm_hidden_dim * self.num_dir

        self.fc1 = nn.Linear(lstm_output_dim, fc_hidden_dim)
        self.fc2 = nn.Linear(fc_hidden_dim, num_classes)

        # Dropout for regularization
        self.dropout_layer = nn.Dropout(dropout)

        # Activation functions
        self.relu = nn.ReLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the network.

        Args:
            x: Input tensor of shape [batch_size, seq_length, n_features]

        Returns:
            Output tensor of shape [batch_size, num_classes]
        """
        # Initialize hidden state and cell state
        h0 = torch.zeros(
            self.lstm_n_layers * self.num_dir, x.size(0), self.lstm_hidden_dim
        ).to(x.device)
        c0 = torch.zeros(
            self.lstm_n_layers * self.num_dir, x.size(0), self.lstm_hidden_dim
        ).to(x.device)

        # Pass through LSTM layers
        # output shape: [batch_size, seq_length, lstm_hidden_dim * num_directions]
        output, (hn, cn) = self.lstm(x, (h0, c0))

        # We use the output from the last time step
        if self.num_dir == 2:
            # For bidirectional, concatenate the last outputs from both directions
            # Take the last time step output
            # Shape: [batch_size, lstm_hidden_dim * 2]
            out_forward = output[:, -1, : self.lstm_hidden_dim]
            out_reverse = output[:, 0, self.lstm_hidden_dim :]
            lstm_out = torch.cat((out_forward, out_reverse), dim=1)
        else:
            # For unidirectional, take only the last time step
            # Shape: [batch_size, lstm_hidden_dim]
            lstm_out = output[:, -1, :]

        # Pass through fully connected layers
        x = self.dropout_layer(lstm_out)
        x = self.fc1(x)
        x = self.relu(x)
        x = self.dropout_layer(x)
        x = self.fc2(x)

        return x

    def predict_character(self, x: torch.Tensor) -> Tuple[str, float]:
        """
        Predict a character from input features.

        Args:
            x: Input tensor of shape [1, seq_length, n_features]

        Returns:
            Tuple of (predicted character, confidence)
        """
        self.eval()
        with torch.no_grad():
            # Forward pass
            output = self.forward(x)

            # Get probabilities
            probabilities = torch.nn.functional.softmax(output, dim=1)

            # Get predicted class and confidence
            confidence, predicted = torch.max(probabilities, 1)

            # Convert to ASCII character
            char_idx = predicted.item()

            # Map to ASCII (32 = space, 33-126 = printable chars)
            character = chr(char_idx + 32)

            return character, confidence.item()


class CharacterPredictor:
    """
    Wrapper class for handwriting character prediction.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
    ):
        """
        Initialize the character predictor.

        Args:
            model_path: Path to pre-trained model (if None, use default)
            device: Device to run inference on ('cuda' or 'cpu')
        """
        self.device = device

        # Create model
        self.model = RemarkableLSTM().to(device)

        # Load pre-trained model if available
        if model_path and os.path.exists(model_path):
            self.model.load_state_dict(torch.load(model_path, map_location=device))
            print(f"Loaded model from {model_path}")
        else:
            print("Using untrained model (predictions will be random)")

        self.model.eval()

    def preprocess_stroke(self, stroke: Dict[str, List[float]]) -> torch.Tensor:
        """
        Preprocess a single stroke for inference.

        Args:
            stroke: Dictionary with keys 'x', 'y', 'p' and optionally 't'

        Returns:
            Tensor of shape [1, seq_length, n_features]
        """
        # Extract coordinates and pressure
        x_points = np.array(stroke["x"], dtype=np.float32)
        y_points = np.array(stroke["y"], dtype=np.float32)
        pressures = np.array(stroke["p"], dtype=np.float32)

        # Compute deltas (dx, dy)
        dx = np.diff(x_points, prepend=x_points[0])
        dy = np.diff(y_points, prepend=y_points[0])

        # Normalize
        x_points = (x_points - np.min(x_points)) / (
            np.max(x_points) - np.min(x_points) + 1e-8
        )
        y_points = (y_points - np.min(y_points)) / (
            np.max(y_points) - np.min(y_points) + 1e-8
        )
        dx = dx / (np.max(np.abs(dx)) + 1e-8)
        dy = dy / (np.max(np.abs(dy)) + 1e-8)

        # Stack features
        features = np.column_stack([x_points, y_points, pressures, dx, dy])

        # Convert to tensor and add batch dimension
        tensor = (
            torch.tensor(features, dtype=torch.float32).unsqueeze(0).to(self.device)
        )

        return tensor

    def predict(self, stroke: Dict[str, List[float]]) -> Tuple[str, float]:
        """
        Predict a character from a single stroke.

        Args:
            stroke: Dictionary with keys 'x', 'y', 'p' and optionally 't'

        Returns:
            Tuple of (predicted character, confidence)
        """
        # Preprocess stroke
        tensor = self.preprocess_stroke(stroke)

        # Predict
        character, confidence = self.model.predict_character(tensor)

        return character, confidence

    def predict_strokes(self, strokes: List[Dict[str, List[float]]]) -> str:
        """
        Predict text from multiple strokes.

        Args:
            strokes: List of stroke dictionaries

        Returns:
            Predicted text
        """
        characters = []

        for stroke in strokes:
            char, conf = self.predict(stroke)
            characters.append(char)

        return "".join(characters)


def train_model(
    model: RemarkableLSTM,
    train_loader: torch.utils.data.DataLoader,
    val_loader: torch.utils.data.DataLoader,
    num_epochs: int = 50,
    learning_rate: float = 0.001,
    device: str = "cuda" if torch.cuda.is_available() else "cpu",
) -> RemarkableLSTM:
    """
    Train the model on a dataset.

    Args:
        model: The RemarkableLSTM model to train
        train_loader: DataLoader for training data
        val_loader: DataLoader for validation data
        num_epochs: Number of training epochs
        learning_rate: Learning rate for optimizer
        device: Device to train on ('cuda' or 'cpu')

    Returns:
        Trained model
    """
    # Move model to device
    model = model.to(device)

    # Define loss function and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    # Training loop
    for epoch in range(num_epochs):
        model.train()
        train_loss = 0.0

        for batch_features, batch_labels in train_loader:
            # Move data to device
            batch_features = batch_features.to(device)
            batch_labels = batch_labels.to(device)

            # Zero gradients
            optimizer.zero_grad()

            # Forward pass
            outputs = model(batch_features)

            # Compute loss
            loss = criterion(outputs, batch_labels)

            # Backward pass and optimize
            loss.backward()
            optimizer.step()

            # Track loss
            train_loss += loss.item()

        # Validate
        model.eval()
        val_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            for batch_features, batch_labels in val_loader:
                # Move data to device
                batch_features = batch_features.to(device)
                batch_labels = batch_labels.to(device)

                # Forward pass
                outputs = model(batch_features)

                # Compute loss
                loss = criterion(outputs, batch_labels)
                val_loss += loss.item()

                # Compute accuracy
                _, predicted = torch.max(outputs, 1)
                total += batch_labels.size(0)
                correct += (predicted == batch_labels).sum().item()

        # Print metrics
        print(
            f"Epoch {epoch+1}/{num_epochs}, "
            f"Train Loss: {train_loss/len(train_loader):.4f}, "
            f"Val Loss: {val_loss/len(val_loader):.4f}, "
            f"Val Accuracy: {100*correct/total:.2f}%"
        )

    return model


# Example of creating a predictor
if __name__ == "__main__":
    # Create predictor
    predictor = CharacterPredictor()

    # Create a test stroke (simple vertical line for 'l')
    test_stroke = {
        "x": [100, 100, 100, 100, 100],
        "y": [100, 110, 120, 130, 140],
        "p": [0.5, 0.6, 0.7, 0.6, 0.5],
    }

    # Predict
    character, confidence = predictor.predict(test_stroke)

    print(f"Predicted character: {character}")
    print(f"Confidence: {confidence:.4f}")
