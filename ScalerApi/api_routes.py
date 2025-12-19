"""
API Routes for DQN-based Kubernetes Resource Scaling
Contains all Flask route handlers separated from core logic
"""

from flask import jsonify, request
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def register_routes(app, scaling_service, config, core_functions):
    """Register all API routes with the Flask app"""
    
    @app.route('/')
    def index():
        """API information"""
        return jsonify({
            'service': 'DQN Kubernetes Resource Scaler',
            'version': '1.0.0',
            'model': 'Deep Q-Network (DQN)',
            'endpoints': {
                'GET /health': 'Health check',
                'GET /config': 'Get current configuration',
                'POST /config': 'Update configuration',
                'GET /pods': 'List all monitored pods',
                'GET /pods/<namespace>/<pod_name>': 'Get specific pod info',
                'POST /scale/pod/<namespace>/<pod_name>': 'Scale specific pod',
                'POST /scale/all': 'Process and scale all pods',
                'GET /decisions': 'Get recent scaling decisions',
                'GET /statistics': 'Get scaling statistics',
                'POST /autoscale/start': 'Start automatic scaling',
                'POST /autoscale/stop': 'Stop automatic scaling',
                'GET /autoscale/status': 'Get auto-scaler status',
                'POST /api/namespaces/<namespace>/pods/<pod_name>/resize': 'Resize pod resources'
            }
        })

    @app.route('/health')
    def health():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'dqn-scaler',
            'timestamp': datetime.now().isoformat()
        })

    @app.route('/config', methods=['GET', 'POST'])
    def config_endpoint():
        """Get or update configuration"""
        if request.method == 'POST':
            try:
                data = request.get_json()

                # Update allowed config fields
                allowed_fields = ['dry_run', 'auto_scale_enabled', 'auto_scale_interval',
                                'scale_factor', 'scaling_cooldown', 'namespaces', 
                                'excluded_deployments', 'excluded_labels']

                updates = {}
                for field in allowed_fields:
                    if field in data:
                        updates[field] = data[field]

                # Use core_functions to properly update config
                if updates:
                    core_functions.update_config(updates)
                    
                    # Update scaling service with new config if needed
                    if 'excluded_deployments' in updates:
                        scaling_service.excluded_deployments = updates['excluded_deployments']
                    if 'excluded_labels' in updates:
                        scaling_service.excluded_labels = updates['excluded_labels']
                    if 'dry_run' in updates:
                        scaling_service.dry_run = updates['dry_run']
                    if 'scale_factor' in updates:
                        scaling_service.scale_factor = updates['scale_factor']

                return jsonify({
                    'success': True,
                    'message': 'Configuration updated',
                    'config': core_functions.get_config()
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 400

        return jsonify(core_functions.get_config())

    @app.route('/pods')
    def list_pods():
        """List all monitored pods"""
        try:
            all_pods = []
            for namespace in core_functions.get_config().get('namespaces', ['default']):
                pods = scaling_service.k8s_client.get_pods(namespace)
                all_pods.extend(pods)
            return jsonify({
                'success': True,
                'count': len(all_pods),
                'pods': all_pods
            })
        except Exception as e:
            logger.error(f"Error listing pods: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/pods/<namespace>/<pod_name>')
    def get_pod_info(namespace, pod_name):
        """Get detailed information about a specific pod"""
        try:
            metrics = scaling_service.k8s_client.get_single_pod_metrics(namespace, pod_name)
            resources = scaling_service.k8s_client.get_pod_resources(namespace, pod_name)

            pod_key = f"{namespace}/{pod_name}"

            return jsonify({
                'success': True,
                'pod': pod_key,
                'metrics': metrics,
                'resources': resources
            })
        except Exception as e:
            logger.error(f"Error getting pod info: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/scale/pod/<namespace>/<pod_name>', methods=['POST'])
    def scale_pod(namespace, pod_name):
        """Process and potentially scale a specific pod"""
        try:
            pod_info = {
                'namespace': namespace,
                'name': pod_name
            }

            # Get owner information
            pods = scaling_service.k8s_client.get_pods(namespace)
            matching_pod = next((p for p in pods if p['name'] == pod_name), None)

            if not matching_pod:
                return jsonify({
                    'success': False,
                    'error': f'Pod {namespace}/{pod_name} not found or not running'
                }), 404

            pod_info['owner'] = matching_pod.get('owner')

            result = scaling_service.process_pod(pod_info)

            if result:
                return jsonify({
                    'success': True,
                    'result': result
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to process pod'
                }), 500

        except Exception as e:
            logger.error(f"Error scaling pod: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/scale/all', methods=['POST'])
    def scale_all():
        """Process and scale all monitored pods"""
        try:
            results = scaling_service.process_all_pods()
            stats = scaling_service.get_statistics()

            return jsonify({
                'success': True,
                'processed': len(results),
                'results': results,
                'statistics': stats,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error in scale_all: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/decisions')
    def get_decisions():
        """Get recent scaling decisions"""
        try:
            limit = request.args.get('limit', 50, type=int)
            decisions = scaling_service.get_recent_decisions(limit)

            return jsonify({
                'success': True,
                'count': len(decisions),
                'decisions': decisions
            })
        except Exception as e:
            logger.error(f"Error getting decisions: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/statistics')
    def get_statistics():
        """Get scaling statistics"""
        try:
            stats = scaling_service.get_statistics()

            return jsonify({
                'success': True,
                'statistics': stats
            })
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/autoscale/start', methods=['POST'])
    def start_autoscale():
        """Start automatic scaling"""
        try:
            core_functions.update_config({'auto_scale_enabled': True})
            core_functions.start_auto_scaler()

            return jsonify({
                'success': True,
                'message': 'Auto-scaling started',
                'interval': core_functions.get_config()['auto_scale_interval']
            })
        except Exception as e:
            logger.error(f"Error starting auto-scale: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/autoscale/stop', methods=['POST'])
    def stop_autoscale():
        """Stop automatic scaling"""
        try:
            core_functions.update_config({'auto_scale_enabled': False})
            core_functions.stop_auto_scaler()

            return jsonify({
                'success': True,
                'message': 'Auto-scaling stopped'
            })
        except Exception as e:
            logger.error(f"Error stopping auto-scale: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/autoscale/status')
    def autoscale_status():
        """Get auto-scaler status"""
        current_config = core_functions.get_config()
        return jsonify({
            'enabled': current_config['auto_scale_enabled'],
            'running': core_functions.is_auto_scaler_running(),
            'interval_seconds': current_config['auto_scale_interval'],
            'thread_alive': core_functions.is_auto_scaler_thread_alive()
        })

    @app.route('/model/info')
    def model_info():
        """Get DQN model information"""
        current_config = core_functions.get_config()
        return jsonify({
            'model_type': 'Deep Q-Network (DQN)',
            'model_path': current_config['model_path'],
            'state_dim': current_config['state_dim'],
            'action_dim': current_config['action_dim'],
            'actions': {
                '0': 'DECREASE',
                '1': 'MAINTAIN',
                '2': 'INCREASE'
            },
            'state_features': [
                'CPU usage (normalized)',
                'Memory usage (normalized)',
                'Network latency (placeholder)',
                'Container count (normalized)',
                'CPU trend',
                'Memory trend',
                'CPU allocation (normalized)',
                'Memory allocation (normalized)'
            ]
        })

    @app.route('/api/namespaces/<namespace>/pods/<pod_name>/resize', methods=['POST'])
    def resize_pod(namespace, pod_name):
        """Resize a pod's container resources in-place"""
        if not scaling_service or not scaling_service.k8s_client:
            return jsonify({'error': 'Kubernetes client not initialized'}), 503
        
        try:
            data = request.get_json()
            if not data or 'containers' not in data:
                return jsonify({'error': 'Missing containers field in request body'}), 400
            
            container_resources = data['containers']
            if not isinstance(container_resources, dict):
                return jsonify({'error': 'Containers field must be a dictionary'}), 400
            
            # Validate container resource format
            for container_name, resources in container_resources.items():
                if not isinstance(resources, dict):
                    return jsonify({'error': f'Invalid resources format for container {container_name}'}), 400
                
                for resource_type in ['requests', 'limits']:
                    if resource_type in resources:
                        if not isinstance(resources[resource_type], dict):
                            return jsonify({'error': f'Invalid {resource_type} format for container {container_name}'}), 400
                        
                        # Validate resource values
                        for resource_name, resource_value in resources[resource_type].items():
                            if resource_name not in ['cpu', 'memory', 'ephemeral-storage']:
                                return jsonify({'error': f'Unsupported resource type: {resource_name}'}), 400
                            
                            if not isinstance(resource_value, str):
                                return jsonify({'error': f'Resource {resource_name} must be a string value'}), 400

            # Check if horizontal fallback is enabled (optional parameter)
            enable_horizontal_fallback = request.args.get('enable_horizontal_fallback', 'true').lower() == 'true'
            
            # Perform the resize (with potential fallback)
            result = scaling_service.k8s_client.resize_pod(pod_name, namespace, container_resources, enable_horizontal_fallback)
            
            if result['success']:
                return jsonify({
                    'message': result['message'],
                    'pod': pod_name,
                    'namespace': namespace,
                    'scaling_method': result['method'],
                    'details': result['details'],
                    'timestamp': datetime.now().isoformat()
                }), 200
            else:
                return jsonify({
                    'error': result['message'],
                    'details': result['details']
                }), 500
                
        except Exception as e:
            logger.error(f"Error resizing pod {pod_name}: {e}")
            return jsonify({'error': str(e)}), 500

    @app.errorhandler(404)
    def not_found(_):
        """Handle 404 errors"""
        return jsonify({
            'success': False,
            'error': 'Endpoint not found'
        }), 404

    @app.errorhandler(500)
    def internal_error(_):
        """Handle 500 errors"""
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500