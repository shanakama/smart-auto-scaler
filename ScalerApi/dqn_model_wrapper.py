import torch
import numpy as np
import sys
import os
from datetime import datetime

# Add final-models directory to path to import the new agent
final_models_path = os.path.join(os.path.dirname(__file__), 'final-models')
sys.path.append(final_models_path)
from dqn_agent_new import DQNAgent


class DQNScalingModel:
    """Wrapper for new multi-head DQN model to provide scaling decisions"""

    def __init__(self, model_path, state_dim=8, action_dim=3):
        """
        Initialize DQN model for inference

        Args:
            model_path: Path to trained DQN model (.pth file)
            state_dim: Dimension of state vector
            action_dim: Number of actions per head (3: decrease, maintain, increase)
        """
        self.model_path = model_path
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Initialize new multi-head agent
        self.agent = DQNAgent(
            state_size=state_dim,
            action_size=action_dim * 2  # CPU + Memory heads
        )

        # Load trained model
        self._load_model()

    def _load_model(self):
        """Load trained DQN model from file"""
        try:
            self.agent.load_model(self.model_path)
            print(f"Multi-head DQN model loaded successfully from {self.model_path}")
            print(f"Device: {self.device}")
        except Exception as e:
            raise Exception(f"Failed to load DQN model: {e}")

    def predict_action(self, state):
        """
        Predict scaling actions for both CPU and Memory from current state

        Args:
            state: Numpy array of shape (state_dim,) representing current metrics

        Returns:
            cpu_action: Integer (0=decrease, 1=maintain, 2=increase) for CPU
            memory_action: Integer (0=decrease, 1=maintain, 2=increase) for Memory
            q_values: Dictionary with CPU and Memory Q-values
            confidence: Dictionary with confidence scores
            future_prediction: Dictionary with predicted future usage
        """
        # Ensure state is numpy array
        if not isinstance(state, np.ndarray):
            state = np.array(state, dtype=np.float32)

        # Get actions from multi-head agent
        cpu_action, memory_action = self.agent.act(state, training=False)

        # Get Q-values for both heads
        cpu_q_values, memory_q_values = self.agent.get_q_values(state)

        # Get future predictions
        future_cpu, future_memory = self.agent.predict_future_usage(state)

        # Calculate confidence (softmax of Q-values)
        def calculate_confidence(q_values):
            q_exp = np.exp(q_values - np.max(q_values))
            q_softmax = q_exp / np.sum(q_exp)
            return np.max(q_softmax)

        cpu_confidence = calculate_confidence(cpu_q_values)
        memory_confidence = calculate_confidence(memory_q_values)

        return {
            'cpu_action': cpu_action,
            'memory_action': memory_action,
            'q_values': {
                'cpu': cpu_q_values.tolist(),
                'memory': memory_q_values.tolist()
            },
            'confidence': {
                'cpu': float(cpu_confidence),
                'memory': float(memory_confidence)
            },
            'future_prediction': {
                'cpu': float(future_cpu),
                'memory': float(future_memory)
            }
        }

    def predict_batch(self, states):
        """
        Predict actions for multiple states

        Args:
            states: List or array of states

        Returns:
            results: List of prediction dictionaries
        """
        results = []
        for state in states:
            result = self.predict_action(state)
            results.append(result)
        return results

    def get_action_name(self, action):
        """Convert action index to human-readable name"""
        action_names = {
            0: "DECREASE",
            1: "MAINTAIN", 
            2: "INCREASE"
        }
        return action_names.get(action, "UNKNOWN")

    def explain_decision(self, state, prediction_result):
        """
        Provide explanation for the scaling decisions

        Args:
            state: Input state vector
            prediction_result: Result from predict_action()

        Returns:
            explanation: Dictionary with decision explanation
        """
        cpu_action = prediction_result['cpu_action']
        memory_action = prediction_result['memory_action']
        cpu_q_values = prediction_result['q_values']['cpu']
        memory_q_values = prediction_result['q_values']['memory']

        explanation = {
            'actions': {
                'cpu': {
                    'action': self.get_action_name(cpu_action),
                    'action_index': int(cpu_action),
                    'confidence': prediction_result['confidence']['cpu']
                },
                'memory': {
                    'action': self.get_action_name(memory_action),
                    'action_index': int(memory_action),
                    'confidence': prediction_result['confidence']['memory']
                }
            },
            'q_values': {
                'cpu': {
                    'decrease': float(cpu_q_values[0]),
                    'maintain': float(cpu_q_values[1]),
                    'increase': float(cpu_q_values[2])
                },
                'memory': {
                    'decrease': float(memory_q_values[0]),
                    'maintain': float(memory_q_values[1]),
                    'increase': float(memory_q_values[2])
                }
            },
            'future_predictions': prediction_result['future_prediction'],
            'state_summary': self._summarize_state(state),
            'reasoning': self._generate_reasoning(state, prediction_result)
        }

        return explanation

    def _summarize_state(self, state):
        """Summarize the input state"""
        return {
            'current_cpu': float(state[0]),
            'current_memory': float(state[1]),
            'cpu_trend': float(state[2]),
            'memory_trend': float(state[3]),
            'hour_sin': float(state[4]),
            'hour_cos': float(state[5]),
            'day_sin': float(state[6]),
            'day_cos': float(state[7])
        }

    def _generate_reasoning(self, state, prediction_result):
        """Generate human-readable reasoning for the decisions"""
        cpu_usage = state[0]
        memory_usage = state[1]
        cpu_trend = state[2]
        memory_trend = state[3]
        
        cpu_action = prediction_result['cpu_action']
        memory_action = prediction_result['memory_action']
        
        future_cpu = prediction_result['future_prediction']['cpu']
        future_memory = prediction_result['future_prediction']['memory']

        reasons = []

        # Analyze current usage
        if cpu_usage > 0.8:
            reasons.append("High CPU utilization detected")
        elif cpu_usage < 0.2:
            reasons.append("Low CPU utilization detected")
            
        if memory_usage > 0.8:
            reasons.append("High memory utilization detected")
        elif memory_usage < 0.2:
            reasons.append("Low memory utilization detected")

        # Analyze trends
        if cpu_trend > 0.1:
            reasons.append("CPU usage trending upward")
        elif cpu_trend < -0.1:
            reasons.append("CPU usage trending downward")
            
        if memory_trend > 0.1:
            reasons.append("Memory usage trending upward")
        elif memory_trend < -0.1:
            reasons.append("Memory usage trending downward")

        # Analyze predictions
        if future_cpu > cpu_usage + 0.1:
            reasons.append("CPU usage expected to increase")
        elif future_cpu < cpu_usage - 0.1:
            reasons.append("CPU usage expected to decrease")
            
        if future_memory > memory_usage + 0.1:
            reasons.append("Memory usage expected to increase")
        elif future_memory < memory_usage - 0.1:
            reasons.append("Memory usage expected to decrease")

        # Action explanations
        action_explanations = []
        if cpu_action == 2:
            action_explanations.append("CPU scale-up recommended")
        elif cpu_action == 0:
            action_explanations.append("CPU scale-down recommended")
        else:
            action_explanations.append("CPU maintenance recommended")
            
        if memory_action == 2:
            action_explanations.append("Memory scale-up recommended")
        elif memory_action == 0:
            action_explanations.append("Memory scale-down recommended")
        else:
            action_explanations.append("Memory maintenance recommended")

        all_reasons = reasons + action_explanations
        return " | ".join(all_reasons) if all_reasons else "Optimal actions based on learned policy"

    def create_state_from_pod_metrics(self, pod_metrics):
        """
        Create state vector from pod metrics
        
        Args:
            pod_metrics: Dictionary with pod metrics
            
        Returns:
            state: Numpy array suitable for DQN input
        """
        # Extract metrics
        cpu_usage = pod_metrics.get('cpu_usage', 0.0)
        memory_usage = pod_metrics.get('memory_usage_mb', 0.0)
        
        # Normalize if limits are provided
        cpu_limit = pod_metrics.get('cpu_limit', 1.0)
        memory_limit = pod_metrics.get('memory_limit_mb', 1024.0)
        
        cpu_normalized = min(cpu_usage / cpu_limit, 1.0) if cpu_limit > 0 else 0.0
        memory_normalized = min(memory_usage / memory_limit, 1.0) if memory_limit > 0 else 0.0
        
        # Calculate trends (simplified - would need historical data for real trends)
        cpu_trend = pod_metrics.get('cpu_trend', 0.0)
        memory_trend = pod_metrics.get('memory_trend', 0.0)
        
        # Time features
        now = datetime.now()
        hour_sin = np.sin(2 * np.pi * now.hour / 24)
        hour_cos = np.cos(2 * np.pi * now.hour / 24)
        day_sin = np.sin(2 * np.pi * now.weekday() / 7)
        day_cos = np.cos(2 * np.pi * now.weekday() / 7)
        
        state = np.array([
            cpu_normalized,
            memory_normalized,
            cpu_trend,
            memory_trend,
            hour_sin,
            hour_cos,
            day_sin,
            day_cos
        ], dtype=np.float32)
        
        return state


# Singleton instance
_model_instance = None

def get_dqn_model(model_path=None):
    """Get or create DQN model singleton"""
    global _model_instance
    if _model_instance is None:
        if model_path is None:
            # Look for new model first, fall back to old location
            new_model_path = os.path.join(
                os.path.dirname(__file__), 
                'final-models',
                'best_model.pth'
            )
            old_model_path = os.path.join(
                os.path.dirname(__file__),
                'final-models', 
                'dqn_model.pth'
            )
            
            if os.path.exists(new_model_path):
                model_path = new_model_path
            else:
                model_path = old_model_path
                
        _model_instance = DQNScalingModel(model_path)
    return _model_instance