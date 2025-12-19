import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
import random
from collections import deque, namedtuple
from typing import Tuple, List


class DQNNetwork(nn.Module):
    """Deep Q-Network for resource scaling decisions"""
    
    def __init__(self, state_size: int = 8, action_size: int = 9, hidden_size: int = 256):
        super(DQNNetwork, self).__init__()
        
        # Multi-head architecture for CPU and Memory predictions
        self.shared_layers = nn.Sequential(
            nn.Linear(state_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.3)
        )
        
        # Separate heads for CPU and Memory decisions
        self.cpu_head = nn.Sequential(
            nn.Linear(hidden_size, 128),
            nn.ReLU(),
            nn.Linear(128, 3)  # 3 actions: decrease, maintain, increase
        )
        
        self.memory_head = nn.Sequential(
            nn.Linear(hidden_size, 128),
            nn.ReLU(),
            nn.Linear(128, 3)  # 3 actions: decrease, maintain, increase
        )
        
        # Future prediction head
        self.prediction_head = nn.Sequential(
            nn.Linear(hidden_size, 128),
            nn.ReLU(),
            nn.Linear(128, 2)  # Predict future CPU and Memory usage
        )
        
    def forward(self, x):
        shared_features = self.shared_layers(x)
        cpu_q_values = self.cpu_head(shared_features)
        memory_q_values = self.memory_head(shared_features)
        future_prediction = self.prediction_head(shared_features)
        
        return cpu_q_values, memory_q_values, future_prediction


class DQNAgent:
    """DQN Agent for Pod Resource Scaling - Inference Only"""
    
    def __init__(self, state_size: int = 8, action_size: int = 9, 
                 learning_rate: float = 0.001, gamma: float = 0.95):
        
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.gamma = gamma
        
        # Neural Networks
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.q_network = DQNNetwork(state_size, action_size).to(self.device)
        
        # For compatibility with old API
        self.policy_net = self.q_network
        
        # Training metrics (for compatibility)
        self.training_step = 0
        self.losses = []
        self.accuracy_history = []
        
    def act(self, state: np.ndarray, training: bool = False) -> Tuple[int, int]:
        """Choose actions using trained policy"""
        # Greedy action (no exploration during inference)
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            cpu_q_values, memory_q_values, _ = self.q_network(state_tensor)
            cpu_action = cpu_q_values.argmax().item()
            memory_action = memory_q_values.argmax().item()
        
        return cpu_action, memory_action
    
    def select_action(self, state: np.ndarray, training: bool = False) -> int:
        """Compatibility method for old API - returns CPU action only"""
        cpu_action, memory_action = self.act(state, training)
        return cpu_action
    
    def get_q_values(self, state: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Get Q-values for both CPU and Memory heads"""
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            cpu_q_values, memory_q_values, _ = self.q_network(state_tensor)
            return cpu_q_values.cpu().numpy()[0], memory_q_values.cpu().numpy()[0]
    
    def predict_future_usage(self, state: np.ndarray) -> Tuple[float, float]:
        """Predict future resource usage"""
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            _, _, predictions = self.q_network(state_tensor)
            future_cpu, future_memory = predictions[0].cpu().numpy()
        
        return float(future_cpu), float(future_memory)
    
    def save_model(self, filepath: str):
        """Save the trained model"""
        torch.save({
            'model_state_dict': self.q_network.state_dict(),
            'training_step': self.training_step,
            'losses': self.losses,
            'accuracy_history': self.accuracy_history
        }, filepath)
    
    def load_model(self, filepath: str):
        """Load a trained model"""
        checkpoint = torch.load(filepath, map_location=self.device)
        self.q_network.load_state_dict(checkpoint['model_state_dict'])
        self.training_step = checkpoint.get('training_step', 0)
        self.losses = checkpoint.get('losses', [])
        self.accuracy_history = checkpoint.get('accuracy_history', [])
        self.q_network.eval()  # Set to evaluation mode
    
    def load(self, filepath: str):
        """Compatibility method for old API"""
        self.load_model(filepath)