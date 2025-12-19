import numpy as np
import logging
from typing import Dict, List, Optional
from collections import deque
from datetime import datetime
from Submission.ScalerApi.dqn_model_wrapper import DQNScalingModel
from k8s_client import KubernetesClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScalingService:
    """Enhanced scaling service with multi-head DQN for CPU and Memory decisions"""

    def __init__(self, config: Dict):
        self.config = config
        self.history_window = config.get('history_window', 5)
        self.scale_factor = config.get('scale_factor', 0.2)
        self.min_cpu = config.get('min_cpu', 0.1)
        self.max_cpu = config.get('max_cpu', 8.0)
        self.min_memory = config.get('min_memory', 128)
        self.max_memory = config.get('max_memory', 16384)
        self.dry_run = config.get('dry_run', False)
        print("Dry run mode:", self.dry_run)

        # Initialize new multi-head DQN model
        model_path = config.get('model_path', 'final-models/best_model.pth')
        self.dqn_model = DQNScalingModel(
            model_path=model_path,
            state_dim=config.get('state_dim', 8),
            action_dim=config.get('action_dim', 3)
        )

        # Initialize Kubernetes client
        self.k8s_client = KubernetesClient(
            in_cluster=config.get('in_cluster', False),
            namespaces=config.get('namespaces', ['default'])
        )
        
        # Check if Kubernetes is available
        if not self.k8s_client.is_available():
            logger.warning("Kubernetes client not available - scaling operations will be simulated")

        # Tracking structures
        self.pod_history = {}  # Historical metrics per pod
        self.scaling_history = {}  # Historical scaling decisions
        self.cooldown_period = config.get('cooldown_minutes', 5)
        self.last_scale_times = {}  # Track last scaling time per pod

    def get_scaling_recommendations(self, pod_metrics: List[Dict]) -> List[Dict]:
        """
        Get scaling recommendations for multiple pods using multi-head DQN

        Args:
            pod_metrics: List of pod metric dictionaries

        Returns:
            List of scaling recommendation dictionaries
        """
        recommendations = []

        for pod_data in pod_metrics:
            try:
                recommendation = self._get_single_pod_recommendation(pod_data)
                recommendations.append(recommendation)
            except Exception as e:
                logger.error(f"Error getting recommendation for pod {pod_data.get('pod_name', 'unknown')}: {e}")
                # Add error recommendation
                recommendations.append({
                    'pod_name': pod_data.get('pod_name', 'unknown'),
                    'namespace': pod_data.get('namespace', 'default'),
                    'error': str(e),
                    'cpu_action': 'MAINTAIN',
                    'memory_action': 'MAINTAIN',
                    'confidence': {'cpu': 0.0, 'memory': 0.0}
                })

        return recommendations

    def _get_single_pod_recommendation(self, pod_data: Dict) -> Dict:
        """Get scaling recommendation for a single pod"""
        pod_name = pod_data.get('pod_name')
        namespace = pod_data.get('namespace', 'default')
        
        # Update pod history
        self._update_pod_history(pod_name, pod_data)
        
        # Create state for DQN
        state = self._create_dqn_state(pod_data, pod_name)
        
        # Get prediction from multi-head DQN
        prediction = self.dqn_model.predict_action(state)
        
        # Check cooldown
        can_scale = self._check_scaling_cooldown(pod_name)
        
        # Get detailed explanation
        explanation = self.dqn_model.explain_decision(state, prediction)
        
        # Calculate resource changes
        cpu_change = self._calculate_resource_change(
            pod_data.get('cpu_usage', 0.0), 
            prediction['cpu_action']
        )
        memory_change = self._calculate_resource_change(
            pod_data.get('memory_usage_mb', 0.0), 
            prediction['memory_action']
        )

        recommendation = {
            'pod_name': pod_name,
            'namespace': namespace,
            'timestamp': datetime.now().isoformat(),
            'current_metrics': {
                'cpu_usage': pod_data.get('cpu_usage', 0.0),
                'memory_usage_mb': pod_data.get('memory_usage_mb', 0.0),
                'cpu_limit': pod_data.get('cpu_limit', 1.0),
                'memory_limit_mb': pod_data.get('memory_limit_mb', 1024.0)
            },
            'predictions': {
                'cpu_action': self.dqn_model.get_action_name(prediction['cpu_action']),
                'memory_action': self.dqn_model.get_action_name(prediction['memory_action']),
                'cpu_action_index': prediction['cpu_action'],
                'memory_action_index': prediction['memory_action']
            },
            'confidence': prediction['confidence'],
            'future_predictions': prediction['future_prediction'],
            'q_values': prediction['q_values'],
            'resource_changes': {
                'cpu': cpu_change,
                'memory': memory_change
            },
            'can_scale': can_scale,
            'explanation': explanation,
            'reasoning': explanation['reasoning']
        }

        # Store scaling decision
        self._store_scaling_decision(pod_name, recommendation)

        return recommendation

    def _create_dqn_state(self, pod_data: Dict, pod_name: str) -> np.ndarray:
        """Create state vector for DQN from pod metrics"""
        # Use the model's method for consistency
        return self.dqn_model.create_state_from_pod_metrics(pod_data)

    def _update_pod_history(self, pod_name: str, pod_data: Dict):
        """Update historical metrics for a pod"""
        if pod_name not in self.pod_history:
            self.pod_history[pod_name] = deque(maxlen=self.history_window)
        
        history_entry = {
            'timestamp': datetime.now(),
            'cpu_usage': pod_data.get('cpu_usage', 0.0),
            'memory_usage_mb': pod_data.get('memory_usage_mb', 0.0),
            'cpu_limit': pod_data.get('cpu_limit', 1.0),
            'memory_limit_mb': pod_data.get('memory_limit_mb', 1024.0)
        }
        
        self.pod_history[pod_name].append(history_entry)

    def _calculate_resource_change(self, current_value: float, action: int) -> Dict:
        """Calculate new resource allocation based on action"""
        multipliers = {0: 0.8, 1: 1.0, 2: 1.2}  # -20%, maintain, +20%
        multiplier = multipliers.get(action, 1.0)
        
        new_value = current_value * multiplier
        change_percent = (multiplier - 1.0) * 100
        
        return {
            'current': current_value,
            'new': new_value,
            'change_percent': change_percent,
            'action': self.dqn_model.get_action_name(action)
        }

    def _check_scaling_cooldown(self, pod_name: str) -> bool:
        """Check if pod can be scaled (not in cooldown period)"""
        if pod_name not in self.last_scale_times:
            return True
        
        last_scale_time = self.last_scale_times[pod_name]
        time_since_last_scale = datetime.now() - last_scale_time
        
        return time_since_last_scale.total_seconds() > (self.cooldown_period * 60)

    def _store_scaling_decision(self, pod_name: str, recommendation: Dict):
        """Store scaling decision for tracking"""
        if pod_name not in self.scaling_history:
            self.scaling_history[pod_name] = deque(maxlen=50)  # Keep last 50 decisions
        
        decision_entry = {
            'timestamp': datetime.now(),
            'cpu_action': recommendation['predictions']['cpu_action'],
            'memory_action': recommendation['predictions']['memory_action'],
            'confidence': recommendation['confidence'],
            'can_scale': recommendation['can_scale']
        }
        
        self.scaling_history[pod_name].append(decision_entry)

    def execute_scaling(self, recommendations: List[Dict]) -> List[Dict]:
        """
        Execute scaling decisions for multiple pods

        Args:
            recommendations: List of scaling recommendations

        Returns:
            List of execution results
        """
        results = []
        
        for rec in recommendations:
            if not rec.get('can_scale', False):
                results.append({
                    'pod_name': rec['pod_name'],
                    'status': 'skipped',
                    'reason': 'cooldown_period',
                    'message': f"Pod {rec['pod_name']} is in cooldown period"
                })
                continue
            
            try:
                result = self._execute_single_scaling(rec)
                results.append(result)
                
                # Update last scale time if successful
                if result['status'] == 'success':
                    self.last_scale_times[rec['pod_name']] = datetime.now()
                    
            except Exception as e:
                logger.error(f"Error executing scaling for pod {rec['pod_name']}: {e}")
                results.append({
                    'pod_name': rec['pod_name'],
                    'status': 'error',
                    'error': str(e)
                })

        return results

    def _execute_single_scaling(self, recommendation: Dict) -> Dict:
        """Execute scaling for a single pod"""
        pod_name = recommendation['pod_name']
        namespace = recommendation['namespace']
        
        # Check if any scaling is needed
        cpu_action = recommendation['predictions']['cpu_action_index']
        memory_action = recommendation['predictions']['memory_action_index']
        
        if cpu_action == 1 and memory_action == 1:  # Both maintain
            return {
                'pod_name': pod_name,
                'status': 'no_action_needed',
                'message': 'No scaling required - maintain current resources'
            }

        if self.dry_run:
            return {
                'pod_name': pod_name,
                'status': 'dry_run',
                'message': 'Scaling simulation successful',
                'cpu_action': recommendation['predictions']['cpu_action'],
                'memory_action': recommendation['predictions']['memory_action'],
                'resource_changes': recommendation['resource_changes']
            }

        # Calculate new resource limits
        current_cpu = recommendation['current_metrics']['cpu_limit']
        current_memory = recommendation['current_metrics']['memory_limit_mb']
        
        new_cpu = self._apply_scaling_action(current_cpu, cpu_action)
        new_memory = self._apply_scaling_action(current_memory, memory_action)
        
        # Apply limits
        new_cpu = max(self.min_cpu, min(self.max_cpu, new_cpu))
        new_memory = max(self.min_memory, min(self.max_memory, new_memory))

        try:
            # Execute scaling via Kubernetes API
            success = self.k8s_client.scale_pod_resources(
                pod_name=pod_name,
                namespace=namespace,
                cpu_limit=new_cpu,
                memory_limit_mb=new_memory
            )
            
            if success:
                return {
                    'pod_name': pod_name,
                    'status': 'success',
                    'message': 'Scaling executed successfully',
                    'previous_resources': {
                        'cpu': current_cpu,
                        'memory': current_memory
                    },
                    'new_resources': {
                        'cpu': new_cpu,
                        'memory': new_memory
                    },
                    'actions': {
                        'cpu': recommendation['predictions']['cpu_action'],
                        'memory': recommendation['predictions']['memory_action']
                    }
                }
            else:
                return {
                    'pod_name': pod_name,
                    'status': 'failed',
                    'message': 'Kubernetes scaling operation failed'
                }
                
        except Exception as e:
            raise Exception(f"Kubernetes scaling failed: {e}")

    def _apply_scaling_action(self, current_value: float, action: int) -> float:
        """Apply scaling action to resource value"""
        multipliers = {0: 0.8, 1: 1.0, 2: 1.2}
        return current_value * multipliers.get(action, 1.0)

    def get_pod_history(self, pod_name: str) -> Dict:
        """Get historical metrics for a pod"""
        if pod_name not in self.pod_history:
            return {'error': f'No history found for pod {pod_name}'}
        
        history = list(self.pod_history[pod_name])
        return {
            'pod_name': pod_name,
            'history_length': len(history),
            'metrics': [
                {
                    'timestamp': entry['timestamp'].isoformat(),
                    'cpu_usage': entry['cpu_usage'],
                    'memory_usage_mb': entry['memory_usage_mb'],
                    'cpu_limit': entry['cpu_limit'],
                    'memory_limit_mb': entry['memory_limit_mb']
                }
                for entry in history
            ]
        }

    def get_scaling_history(self, pod_name: str) -> Dict:
        """Get scaling decision history for a pod"""
        if pod_name not in self.scaling_history:
            return {'error': f'No scaling history found for pod {pod_name}'}
        
        history = list(self.scaling_history[pod_name])
        return {
            'pod_name': pod_name,
            'history_length': len(history),
            'decisions': [
                {
                    'timestamp': entry['timestamp'].isoformat(),
                    'cpu_action': entry['cpu_action'],
                    'memory_action': entry['memory_action'],
                    'confidence': entry['confidence'],
                    'can_scale': entry['can_scale']
                }
                for entry in history
            ]
        }