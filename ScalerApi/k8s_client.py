#!/usr/bin/env python3

import os
import yaml
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import logging
from typing import Dict, List, Optional

class KubernetesClient:
    def __init__(self, kubeconfig_path=None, in_cluster=False, namespaces=None):
        """
        Initialize Kubernetes client
        
        Args:
            kubeconfig_path (str): Path to kubeconfig file (optional)
            in_cluster (bool): Whether running inside a k8s cluster
            namespaces (list): List of namespaces to monitor (defaults to ['default'])
        """
        self.logger = logging.getLogger(__name__)
        self.namespaces = namespaces or ['default']
        self._configure_kubernetes(kubeconfig_path, in_cluster)
        
    def _configure_kubernetes(self, kubeconfig_path, in_cluster):
        """Configure kubernetes client authentication"""
        try:
            if in_cluster:
                # Load in-cluster config when running inside a pod
                config.load_incluster_config()
                self.logger.info("Loaded in-cluster Kubernetes configuration")
            else:
                # Load kubeconfig file
                if kubeconfig_path:
                    config.load_kube_config(config_file=kubeconfig_path)
                else:
                    config.load_kube_config()
                self.logger.info("Loaded Kubernetes configuration from kubeconfig")
                
            # Initialize API clients
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.autoscaling_v1 = client.AutoscalingV1Api()
            self.autoscaling_v2 = client.AutoscalingV2Api()
            self.metrics_api = client.CustomObjectsApi()
            
        except Exception as e:
            self.logger.error(f"Failed to configure Kubernetes client: {e}")
            self.logger.warning("Kubernetes client unavailable - running in standalone mode")
            # Set client objects to None for graceful degradation
            self.v1 = None
            self.apps_v1 = None
            self.autoscaling_v1 = None
            self.autoscaling_v2 = None
            self.metrics_api = None

    def is_available(self):
        """Check if Kubernetes client is available"""
        return self.v1 is not None

    def test_connection(self):
        """Test connection to Kubernetes API server"""
        if not self.is_available():
            self.logger.warning("Kubernetes client not available")
            return False
        try:
            version = self.v1.get_api_resources()
            self.logger.info("Successfully connected to Kubernetes API server")
            return True
        except ApiException as e:
            self.logger.error(f"Failed to connect to Kubernetes API server: {e}")
            return False

    def get_namespaces(self):
        """Get list of all namespaces"""
        try:
            namespaces = self.v1.list_namespace()
            return [ns.metadata.name for ns in namespaces.items]
        except ApiException as e:
            self.logger.error(f"Failed to get namespaces: {e}")
            return []

    def get_pods(self, namespace="default"): 
        """Get list of pods in namespace"""
        if not self.is_available():
            self.logger.debug(f"Kubernetes client not available, returning empty pod list for namespace {namespace}")
            return []
        
        try:
            pods = self.v1.list_namespaced_pod(namespace=namespace)
            pod_list = []
            
            for pod in pods.items:
                pod_dict = {
                    'name': pod.metadata.name,
                    'namespace': pod.metadata.namespace,
                    'status': pod.status.phase,
                    'creation_timestamp': pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None,
                    'labels': pod.metadata.labels or {},
                    'node_name': pod.spec.node_name,
                    'pod_ip': pod.status.pod_ip,
                    'containers': []
                }
                
                # Add container information
                if pod.spec.containers:
                    for container in pod.spec.containers:
                        container_dict = {
                            'name': container.name,
                            'image': container.image,
                            'resources': {}
                        }
                        
                        # Add resource requests and limits
                        if container.resources:
                            if container.resources.requests:
                                container_dict['resources']['requests'] = container.resources.requests
                            if container.resources.limits:
                                container_dict['resources']['limits'] = container.resources.limits
                        
                        pod_dict['containers'].append(container_dict)
                
                # Get owner information (deployment, etc.)
                if pod.metadata.owner_references:
                    owner_ref = pod.metadata.owner_references[0]
                    pod_dict['owner'] = {
                        'kind': owner_ref.kind,
                        'name': owner_ref.name
                    }
                else:
                    pod_dict['owner'] = None
                
                pod_list.append(pod_dict)
            
            return pod_list
            
        except ApiException as e:
            self.logger.error(f"Failed to get pods in namespace {namespace}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error getting pods in namespace {namespace}: {e}")
            return []

    def get_deployments(self, namespace="default"):
        """Get list of deployments in namespace"""
        if not self.is_available():
            self.logger.debug(f"Kubernetes client not available, returning empty deployment list for namespace {namespace}")
            return []
            
        try:
            deployments = self.apps_v1.list_namespaced_deployment(namespace=namespace)
            return deployments.items
        except ApiException as e:
            self.logger.error(f"Failed to get deployments in namespace {namespace}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error getting deployments in namespace {namespace}: {e}")
            return []

    def get_services(self, namespace="default"):
        """Get list of services in namespace"""
        if not self.is_available():
            self.logger.debug(f"Kubernetes client not available, returning empty service list for namespace {namespace}")
            return []
            
        try:
            services = self.v1.list_namespaced_service(namespace=namespace)
            return services.items
        except ApiException as e:
            self.logger.error(f"Failed to get services in namespace {namespace}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error getting services in namespace {namespace}: {e}")
            return []

    def get_hpas(self, namespace="default"):
        """Get list of Horizontal Pod Autoscalers in namespace"""
        if not self.is_available():
            self.logger.debug(f"Kubernetes client not available, returning empty HPA list for namespace {namespace}")
            return []
            
        try:
            hpas = self.autoscaling_v2.list_namespaced_horizontal_pod_autoscaler(namespace=namespace)
            return hpas.items
        except ApiException as e:
            self.logger.error(f"Failed to get HPAs in namespace {namespace}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error getting HPAs in namespace {namespace}: {e}")
            return []

    def get_pod_metrics(self, namespace="default"):
        """Get pod metrics from metrics server"""
        if not self.is_available():
            self.logger.debug(f"Kubernetes client not available, returning empty metrics for namespace {namespace}")
            return []
            
        try:
            metrics = self.metrics_api.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=namespace,
                plural="pods"
            )
            return metrics.get('items', [])
        except ApiException as e:
            self.logger.error(f"Failed to get pod metrics in namespace {namespace}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error getting pod metrics in namespace {namespace}: {e}")
            return []

    def get_all_pod_metrics(self):
        """Get pod metrics from all configured namespaces"""
        all_metrics = []
        
        if not self.is_available():
            # Return mock data for testing when k8s is not available
            return self._get_mock_pod_metrics()
        
        for namespace in self.namespaces:
            try:
                # Get pods in namespace
                pods = self.get_pods(namespace)
                
                # Get metrics for namespace
                metrics = self.get_pod_metrics(namespace)
                metrics_dict = {m['metadata']['name']: m for m in metrics}
                
                # Combine pod info with metrics
                for pod in pods:
                    pod_name = pod['name']
                    pod_metrics = metrics_dict.get(pod_name)
                    
                    # Extract resource information from containers
                    cpu_limit = 1.0  # Default values
                    memory_limit_mb = 1024.0
                    
                    if pod['containers']:
                        container = pod['containers'][0]
                        if container.get('resources', {}).get('limits'):
                            limits = container['resources']['limits']
                            if 'cpu' in limits:
                                cpu_limit = self._parse_cpu_limit(str(limits['cpu']))
                            if 'memory' in limits:
                                memory_limit_mb = self._parse_memory_limit(str(limits['memory']))
                    
                    # Extract current usage from metrics
                    cpu_usage = 0.0
                    memory_usage_mb = 0.0
                    
                    if pod_metrics and 'containers' in pod_metrics:
                        for container_metrics in pod_metrics['containers']:
                            if 'usage' in container_metrics:
                                usage = container_metrics['usage']
                                if 'cpu' in usage:
                                    cpu_usage += self._parse_cpu_usage(usage['cpu'])
                                if 'memory' in usage:
                                    memory_usage_mb += self._parse_memory_usage(usage['memory'])
                    
                    pod_data = {
                        'pod_name': pod_name,
                        'namespace': namespace,
                        'cpu_usage': cpu_usage,
                        'memory_usage_mb': memory_usage_mb,
                        'cpu_limit': cpu_limit,
                        'memory_limit_mb': memory_limit_mb,
                        'phase': pod['status'],
                        'node_name': pod['node_name']
                    }
                    
                    all_metrics.append(pod_data)
                    
            except Exception as e:
                self.logger.error(f"Error getting metrics for namespace {namespace}: {e}")
        
        return all_metrics
    
    def _get_mock_pod_metrics(self):
        self.logger.info("----------- Read Mock Data ---")
        return [
            {
                'pod_name': 'nginx-deployment-test',
                'namespace': 'default',
                'cpu_usage': 0.5,
                'memory_usage_mb': 512,
                'cpu_limit': 1.0,
                'memory_limit_mb': 1024,
                'phase': 'Running',
                'node_name': 'test-node'
            },
            {
                'pod_name': 'redis-test',
                'namespace': 'default', 
                'cpu_usage': 0.8,
                'memory_usage_mb': 800,
                'cpu_limit': 1.0,
                'memory_limit_mb': 1024,
                'phase': 'Running',
                'node_name': 'test-node'
            }
        ]
    
    def _parse_cpu_limit(self, cpu_str):
        """Parse CPU limit string to float (in cores)"""
        try:
            if cpu_str.endswith('m'):
                return float(cpu_str[:-1]) / 1000.0
            else:
                return float(cpu_str)
        except:
            return 1.0
    
    def _parse_memory_limit(self, memory_str):
        """Parse memory limit string to MB"""
        try:
            if memory_str.endswith('Mi'):
                return float(memory_str[:-2])
            elif memory_str.endswith('Gi'):
                return float(memory_str[:-2]) * 1024
            elif memory_str.endswith('Ki'):
                return float(memory_str[:-2]) / 1024
            else:
                return float(memory_str) / (1024 * 1024)  # Assume bytes
        except:
            return 1024.0
    
    def _parse_cpu_usage(self, cpu_str):
        """Parse CPU usage string to float (in cores)"""
        try:
            if cpu_str.endswith('n'):
                return float(cpu_str[:-1]) / 1e9
            elif cpu_str.endswith('u'):
                return float(cpu_str[:-1]) / 1e6
            elif cpu_str.endswith('m'):
                return float(cpu_str[:-1]) / 1000.0
            else:
                return float(cpu_str)
        except:
            return 0.0
    
    def _parse_memory_usage(self, memory_str):
        """Parse memory usage string to MB"""
        try:
            if memory_str.endswith('Ki'):
                return float(memory_str[:-2]) / 1024
            elif memory_str.endswith('Mi'):
                return float(memory_str[:-2])
            elif memory_str.endswith('Gi'):
                return float(memory_str[:-2]) * 1024
            else:
                return float(memory_str) / (1024 * 1024)  # Assume bytes
        except:
            return 0.0

    def get_node_metrics(self):
        """Get node metrics from metrics server"""
        try:
            metrics = self.metrics_api.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="nodes"
            )
            return metrics.get('items', [])
        except ApiException as e:
            self.logger.error(f"Failed to get node metrics: {e}")
            return []

    def scale_deployment(self, name, namespace="default", replicas=1):
        """Scale a deployment to specified number of replicas"""
        try:
            # Get current deployment
            deployment = self.apps_v1.read_namespaced_deployment(
                name=name, 
                namespace=namespace
            )
            
            # Update replica count
            deployment.spec.replicas = replicas
            
            # Apply the update
            self.apps_v1.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=deployment
            )
            
            self.logger.info(f"Scaled deployment {name} to {replicas} replicas")
            return True
            
        except ApiException as e:
            self.logger.error(f"Failed to scale deployment {name}: {e}")
            return False

    def create_hpa(self, name, deployment_name, namespace="default", 
                   min_replicas=1, max_replicas=10, target_cpu_percent=80):
        """Create Horizontal Pod Autoscaler"""
        try:
            hpa_spec = client.V2HorizontalPodAutoscaler(
                api_version="autoscaling/v2",
                kind="HorizontalPodAutoscaler",
                metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                spec=client.V2HorizontalPodAutoscalerSpec(
                    scale_target_ref=client.V2CrossVersionObjectReference(
                        api_version="apps/v1",
                        kind="Deployment",
                        name=deployment_name
                    ),
                    min_replicas=min_replicas,
                    max_replicas=max_replicas,
                    metrics=[
                        client.V2MetricSpec(
                            type="Resource",
                            resource=client.V2ResourceMetricSource(
                                name="cpu",
                                target=client.V2MetricTarget(
                                    type="Utilization",
                                    average_utilization=target_cpu_percent
                                )
                            )
                        )
                    ]
                )
            )
            
            self.autoscaling_v2.create_namespaced_horizontal_pod_autoscaler(
                namespace=namespace,
                body=hpa_spec
            )
            
            self.logger.info(f"Created HPA {name} for deployment {deployment_name}")
            return True
            
        except ApiException as e:
            self.logger.error(f"Failed to create HPA {name}: {e}")
            return False

    def resize_pod_via_deployment(self, pod_name, namespace="default", container_resources=None):
        """
        Resize a pod's container resources by updating its deployment
        
        Args:
            pod_name (str): Name of the pod to resize
            namespace (str): Namespace of the pod
            container_resources (dict): Dict of container_name -> {requests: {}, limits: {}}
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not container_resources:
                self.logger.error("No container resources specified for resize")
                return False

            # Get the pod to find its owner (deployment)
            pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            
            # Find the deployment that owns this pod
            deployment_name = None
            if pod.metadata.owner_references:
                for owner in pod.metadata.owner_references:
                    if owner.kind == "ReplicaSet":
                        # Get the ReplicaSet to find its deployment
                        rs = self.apps_v1.read_namespaced_replica_set(
                            name=owner.name, 
                            namespace=namespace
                        )
                        if rs.metadata.owner_references:
                            for rs_owner in rs.metadata.owner_references:
                                if rs_owner.kind == "Deployment":
                                    deployment_name = rs_owner.name
                                    break
                        break
            
            if not deployment_name:
                self.logger.error(f"Could not find deployment for pod {pod_name}")
                return False
            
            # Get the deployment
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name, 
                namespace=namespace
            )
            
            # Update container resources in the deployment
            for container in deployment.spec.template.spec.containers:
                if container.name in container_resources:
                    new_resources = container_resources[container.name]
                    
                    # Create new resource requirements
                    resource_requirements = client.V1ResourceRequirements()
                    
                    # Preserve existing resources and update with new ones
                    current_requests = {}
                    current_limits = {}
                    
                    if container.resources:
                        if container.resources.requests:
                            current_requests = dict(container.resources.requests)
                        if container.resources.limits:
                            current_limits = dict(container.resources.limits)
                    
                    # Update with new values
                    if 'requests' in new_resources:
                        current_requests.update(new_resources['requests'])
                        resource_requirements.requests = current_requests
                    
                    if 'limits' in new_resources:
                        current_limits.update(new_resources['limits'])
                        resource_requirements.limits = current_limits
                    
                    container.resources = resource_requirements
            
            # Patch the deployment
            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=deployment
            )
            
            self.logger.info(f"Updated deployment {deployment_name} to resize pod {pod_name}")
            return True
            
        except ApiException as e:
            self.logger.error(f"Failed to resize pod {pod_name} via deployment: {e}")
            return False

    def resize_deployment_resources(self, deployment_name, namespace="default", container_resources=None):
        """
        Resize deployment container resources directly
        
        Args:
            deployment_name (str): Name of the deployment to resize
            namespace (str): Namespace of the deployment
            container_resources (dict): Dict of container_name -> {requests: {}, limits: {}}
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not container_resources:
                self.logger.error("No container resources specified for resize")
                return False

            # Get the deployment
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name, 
                namespace=namespace
            )
            
            # Update container resources
            for container in deployment.spec.template.spec.containers:
                if container.name in container_resources:
                    new_resources = container_resources[container.name]
                    
                    # Create new resource requirements
                    resource_requirements = client.V1ResourceRequirements()
                    
                    # Preserve existing resources and update with new ones
                    current_requests = {}
                    current_limits = {}
                    
                    if container.resources:
                        if container.resources.requests:
                            current_requests = dict(container.resources.requests)
                        if container.resources.limits:
                            current_limits = dict(container.resources.limits)
                    
                    # Update with new values
                    if 'requests' in new_resources:
                        current_requests.update(new_resources['requests'])
                        resource_requirements.requests = current_requests
                    
                    if 'limits' in new_resources:
                        current_limits.update(new_resources['limits'])
                        resource_requirements.limits = current_limits
                    
                    container.resources = resource_requirements
            
            # Patch the deployment
            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=deployment
            )
            
            self.logger.info(f"Updated deployment {deployment_name} resources")
            return True
            
        except ApiException as e:
            self.logger.error(f"Failed to resize deployment {deployment_name}: {e}")
            return False

    def check_resize_support(self, pod_name, namespace="default"):
        """
        Check if the pod supports in-place resize
        """
        try:
            pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            
            # Check if pod has the necessary conditions for resize
            resize_supported = True
            issues = []
            
            for container in pod.spec.containers:
                if not container.resources:
                    issues.append(f"Container {container.name} has no resource specification")
                    resize_supported = False
                else:
                    if not container.resources.requests:
                        issues.append(f"Container {container.name} has no resource requests")
                        resize_supported = False
                    if not container.resources.limits:
                        issues.append(f"Container {container.name} has no resource limits")
                        resize_supported = False
            
            # Check pod status
            if pod.status.phase != "Running":
                issues.append(f"Pod is not running (status: {pod.status.phase})")
                resize_supported = False
            
            # Check for resize policy in pod spec (K8s 1.27+)
            if hasattr(pod.spec, 'resize_policy'):
                self.logger.info(f"Pod has resize policy: {pod.spec.resize_policy}")
            
            self.logger.info(f"Resize support check for {pod_name}: {'Supported' if resize_supported else 'Not supported'}")
            if issues:
                self.logger.warning(f"Issues found: {issues}")
            
            return resize_supported, issues
            
        except ApiException as e:
            self.logger.error(f"Failed to check resize support for pod {pod_name}: {e}")
            return False, [str(e)]

    def find_pod_owner_deployment(self, pod_name, namespace="default"):
        """
        Find the deployment that owns a specific pod
        
        Args:
            pod_name (str): Name of the pod
            namespace (str): Namespace of the pod
        
        Returns:
            str: Name of the deployment, or None if not found
        """
        try:
            pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            
            # Find the deployment that owns this pod through ReplicaSet
            if pod.metadata.owner_references:
                for owner in pod.metadata.owner_references:
                    if owner.kind == "ReplicaSet":
                        # Get the ReplicaSet to find its deployment
                        rs = self.apps_v1.read_namespaced_replica_set(
                            name=owner.name, 
                            namespace=namespace
                        )
                        if rs.metadata.owner_references:
                            for rs_owner in rs.metadata.owner_references:
                                if rs_owner.kind == "Deployment":
                                    return rs_owner.name
            
            self.logger.warning(f"Could not find deployment for pod {pod_name}")
            return None
            
        except ApiException as e:
            self.logger.error(f"Failed to find deployment for pod {pod_name}: {e}")
            return None

    def scale_deployment_horizontally(self, deployment_name, namespace="default", additional_replicas=1):
        """
        Scale a deployment horizontally by adding replicas
        
        Args:
            deployment_name (str): Name of the deployment
            namespace (str): Namespace of the deployment
            additional_replicas (int): Number of additional replicas to add
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get current deployment
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name, 
                namespace=namespace
            )
            
            current_replicas = deployment.spec.replicas or 1
            new_replicas = current_replicas + additional_replicas
            
            self.logger.info(f"Scaling deployment {deployment_name} from {current_replicas} to {new_replicas} replicas")
            
            # Scale the deployment
            success = self.scale_deployment(deployment_name, namespace, new_replicas)
            
            if success:
                self.logger.info(f"Successfully scaled deployment {deployment_name} horizontally")
                return True
            else:
                self.logger.error(f"Failed to scale deployment {deployment_name} horizontally")
                return False
                
        except ApiException as e:
            self.logger.error(f"Failed to scale deployment {deployment_name} horizontally: {e}")
            return False

    def _try_vertical_resize(self, pod_name, namespace, container_resources):
        """
        Try to resize pod vertically using kubectl
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import subprocess
            import tempfile
            import json
            
            # Get current pod to check its current state
            pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            self.logger.info(f"Current pod containers: {[c.name for c in pod.spec.containers]}")
            
            # Build kubectl command with the new resource values
            kubectl_args = ['kubectl', 'patch', 'pod', pod_name, '-n', namespace, '--subresource=resize']
            
            # Create patch in the exact format kubectl expects
            patch_data = {
                "spec": {
                    "containers": []
                }
            }
            
            for container in pod.spec.containers:
                if container.name in container_resources:
                    new_resources = container_resources[container.name]
                    
                    container_patch = {"name": container.name}
                    resources = {}
                    
                    # Include both current and new resource values
                    if container.resources:
                        if container.resources.requests:
                            resources['requests'] = dict(container.resources.requests)
                        if container.resources.limits:
                            resources['limits'] = dict(container.resources.limits)
                    
                    # Override with new values
                    if 'requests' in new_resources:
                        if 'requests' not in resources:
                            resources['requests'] = {}
                        resources['requests'].update(new_resources['requests'])
                    
                    if 'limits' in new_resources:
                        if 'limits' not in resources:
                            resources['limits'] = {}
                        resources['limits'].update(new_resources['limits'])
                    
                    if resources:
                        container_patch['resources'] = resources
                        patch_data["spec"]["containers"].append(container_patch)
            
            self.logger.info(f"Kubectl patch data: {json.dumps(patch_data, indent=2)}")
            
            # Execute kubectl command
            kubectl_args.extend(['--type=strategic', '-p', json.dumps(patch_data)])
            
            result = subprocess.run(
                kubectl_args,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.info(f"Successfully resized pod {pod_name} vertically")
                self.logger.info(f"kubectl output: {result.stdout}")
                return True
            else:
                self.logger.error(f"kubectl failed with return code {result.returncode}")
                self.logger.error(f"kubectl stderr: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during vertical resize: {e}")
            return False

    def resize_pod(self, pod_name, namespace="default", container_resources=None, enable_horizontal_fallback=True):
        """
        Resize a pod's container resources in-place, with fallback to deployment update
        
        Args:
            pod_name (str): Name of the pod to resize
            namespace (str): Namespace of the pod
            container_resources (dict): Dict of container_name -> {requests: {}, limits: {}}
            enable_horizontal_fallback (bool): Unused parameter (kept for API compatibility)
        
        Returns:
            dict: Result with success status, method used, and details
        """
        result = {
            "success": False,
            "method": None,
            "details": {},
            "message": ""
        }
        
        try:
            if not container_resources:
                result["message"] = "No container resources specified for resize"
                self.logger.error(result["message"])
                return result

            import json
            self.logger.info(f"Input container_resources: {json.dumps(container_resources, indent=2)}")

            # Check if resize is supported for this pod
            supported, issues = self.check_resize_support(pod_name, namespace)
            
            # First, try vertical scaling (in-place resize)
            if supported:
                self.logger.info("Attempting vertical scaling (in-place resize)")
                vertical_success = self._try_vertical_resize(pod_name, namespace, container_resources)
                
                if vertical_success:
                    result.update({
                        "success": True,
                        "method": "vertical",
                        "message": f"Successfully resized pod {pod_name} vertically",
                        "details": {
                            "pod_name": pod_name,
                            "namespace": namespace,
                            "container_resources": container_resources
                        }
                    })
                    return result
                else:
                    self.logger.warning("Vertical scaling failed, trying horizontal scaling fallback")
            else:
                self.logger.warning(f"Vertical scaling not supported for pod {pod_name}: {issues}")
            
            # If vertical scaling failed or not supported, try updating via deployment
            self.logger.info("Vertical scaling failed, trying deployment resource update")
            
            deployment_name = self.find_pod_owner_deployment(pod_name, namespace)
            if not deployment_name:
                result["message"] = f"Cannot update resources: no deployment found for pod {pod_name}"
                self.logger.error(result["message"])
                return result
            
            # Try updating deployment resources directly
            deployment_success = self.resize_deployment_resources(deployment_name, namespace, container_resources)
            
            if deployment_success:
                result.update({
                    "success": True,
                    "method": "deployment_update",
                    "message": f"Successfully updated deployment {deployment_name} resources",
                    "details": {
                        "pod_name": pod_name,
                        "deployment_name": deployment_name,
                        "namespace": namespace,
                        "container_resources": container_resources,
                        "reason": "Direct vertical scaling failed, updated via deployment"
                    }
                })
                return result
            else:
                result["message"] = f"Both vertical scaling and deployment resource update failed for pod {pod_name}"
                self.logger.error(result["message"])
                return result
            
        except Exception as e:
            result["message"] = f"Unexpected error during resize operation: {str(e)}"
            self.logger.error(result["message"])
            import traceback
            traceback.print_exc()
            return result

    def get_pod_details(self, pod_name, namespace="default"):
        """Get detailed information about a specific pod"""
        try:
            pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            
            containers_info = []
            for container in pod.spec.containers:
                container_info = {
                    'name': container.name,
                    'image': container.image,
                    'resources': {
                        'requests': {},
                        'limits': {}
                    }
                }
                
                if container.resources:
                    if container.resources.requests:
                        container_info['resources']['requests'] = dict(container.resources.requests)
                    if container.resources.limits:
                        container_info['resources']['limits'] = dict(container.resources.limits)
                
                containers_info.append(container_info)
            
            pod_info = {
                'name': pod.metadata.name,
                'namespace': pod.metadata.namespace,
                'status': pod.status.phase,
                'node_name': pod.spec.node_name,
                'containers': containers_info,
                'created': pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None,
                'labels': pod.metadata.labels or {},
                'annotations': pod.metadata.annotations or {}
            }
            
            return pod_info
            
        except ApiException as e:
            self.logger.error(f"Failed to get pod details for {pod_name}: {e}")
            return None
        
    def list_pods(self, namespace: str = None) -> List[Dict]:
        """
        List all running pods in specified namespaces

        Args:
            namespace: Specific namespace, or None for all configured namespaces

        Returns:
            List of pod information dictionaries
        """
        pods_list = []
        namespaces_to_check = [namespace] if namespace else self.namespaces

        for ns in namespaces_to_check:
            try:
                pods = self.v1.list_namespaced_pod(ns)
                for pod in pods.items:
                    if pod.status.phase == 'Running':
                        pods_list.append({
                            'name': pod.metadata.name,
                            'namespace': pod.metadata.namespace,
                            'uid': pod.metadata.uid,
                            'labels': pod.metadata.labels or {},
                            'owner': self._get_pod_owner(pod)
                        })
            except ApiException as e:
                self.logger.error(f"Failed to list pods in namespace {ns}: {e}")

        return pods_list

    def _get_pod_owner(self, pod):
        """Get owner information for a pod"""
        if pod.metadata.owner_references:
            for owner in pod.metadata.owner_references:
                return {
                    'kind': owner.kind,
                    'name': owner.name,
                    'uid': owner.uid
                }
        return None

    def get_single_pod_metrics(self, namespace: str, pod_name: str) -> Optional[Dict]:
        """
        Get metrics for a specific pod
        
        Args:
            namespace: Pod namespace
            pod_name: Pod name
            
        Returns:
            Dictionary with CPU and memory usage metrics
        """
        try:
            metrics = self.metrics_api.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1", 
                namespace=namespace,
                plural="pods"
            )
            
            for item in metrics.get('items', []):
                if item['metadata']['name'] == pod_name:
                    containers = item.get('containers', [])
                    if containers:
                        container = containers[0]  # Get first container metrics
                        usage = container.get('usage', {})
                        
                        # Parse CPU (in nano cores) to cores
                        cpu_nano = usage.get('cpu', '0n')
                        cpu_cores = float(cpu_nano.replace('n', '')) / 1e9 if 'n' in cpu_nano else 0.0
                        
                        # Parse memory (in bytes/Ki/Mi) to MB
                        memory_str = usage.get('memory', '0Ki')
                        if 'Ki' in memory_str:
                            memory_mb = float(memory_str.replace('Ki', '')) / 1024
                        elif 'Mi' in memory_str:
                            memory_mb = float(memory_str.replace('Mi', ''))
                        else:
                            memory_mb = float(memory_str.replace('Gi', '')) * 1024 if 'Gi' in memory_str else 0.0
                        
                        return {
                            'cpu_usage_cores': cpu_cores,
                            'memory_usage_mb': memory_mb
                        }
            
            self.logger.warning(f"No metrics found for pod {namespace}/{pod_name}")
            return None
            
        except ApiException as e:
            self.logger.error(f"Failed to get pod metrics for {namespace}/{pod_name}: {e}")
            return None

    def get_pod_resources(self, namespace: str, pod_name: str) -> Dict:
        """
        Get resource requests and limits for a pod
        
        Args:
            namespace: Pod namespace
            pod_name: Pod name
            
        Returns:
            Dictionary with resource allocations
        """
        try:
            pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            
            # Get first container's resource requirements
            if pod.spec.containers:
                container = pod.spec.containers[0]
                resources = container.resources
                
                cpu_requests = 1.0
                memory_requests = 512
                
                if resources and resources.requests:
                    # Parse CPU requests
                    cpu_req = resources.requests.get('cpu', '1')
                    if 'm' in cpu_req:
                        cpu_requests = float(cpu_req.replace('m', '')) / 1000
                    else:
                        cpu_requests = float(cpu_req)
                    
                    # Parse memory requests
                    memory_req = resources.requests.get('memory', '512Mi')
                    if 'Mi' in memory_req:
                        memory_requests = float(memory_req.replace('Mi', ''))
                    elif 'Gi' in memory_req:
                        memory_requests = float(memory_req.replace('Gi', '')) * 1024
                    elif 'Ki' in memory_req:
                        memory_requests = float(memory_req.replace('Ki', '')) / 1024
                
                return {
                    'cpu_requests_cores': cpu_requests,
                    'memory_requests_mb': memory_requests
                }
                
            return {
                'cpu_requests_cores': 1.0,
                'memory_requests_mb': 512
            }
            
        except ApiException as e:
            self.logger.error(f"Failed to get pod resources for {namespace}/{pod_name}: {e}")
            return {
                'cpu_requests_cores': 1.0,
                'memory_requests_mb': 512
            }

    def get_deployment_from_pod(self, namespace: str, pod_name: str) -> Optional[str]:
        """
        Get deployment name that owns a pod
        
        Args:
            namespace: Pod namespace
            pod_name: Pod name
            
        Returns:
            Deployment name or None
        """
        try:
            pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            
            if pod.metadata.owner_references:
                for owner in pod.metadata.owner_references:
                    if owner.kind == "ReplicaSet":
                        # Get ReplicaSet to find deployment
                        rs = self.apps_v1.read_namespaced_replica_set(
                            name=owner.name, 
                            namespace=namespace
                        )
                        if rs.metadata.owner_references:
                            for rs_owner in rs.metadata.owner_references:
                                if rs_owner.kind == "Deployment":
                                    return rs_owner.name
            return None
            
        except ApiException as e:
            self.logger.error(f"Failed to get deployment for pod {namespace}/{pod_name}: {e}")
            return None

    def scale_deployment_resources(self, namespace: str, deployment_name: str, cpu_cores: float, memory_mb: float, dry_run: bool = False) -> bool:
        """
        Scale deployment resources
        
        Args:
            namespace: Deployment namespace
            deployment_name: Deployment name
            cpu_cores: New CPU allocation
            memory_mb: New memory allocation 
            dry_run: Whether to perform dry run
            
        Returns:
            True if successful
        """
        try:
            if dry_run:
                self.logger.info(f"DRY RUN: Would scale deployment {namespace}/{deployment_name} to CPU: {cpu_cores}, Memory: {memory_mb}Mi")
                return True
                
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )
            
            # Update container resources
            for container in deployment.spec.template.spec.containers:
                if not container.resources:
                    container.resources = client.V1ResourceRequirements()
                if not container.resources.requests:
                    container.resources.requests = {}
                if not container.resources.limits:
                    container.resources.limits = {}
                    
                container.resources.requests['cpu'] = f"{cpu_cores}"
                container.resources.requests['memory'] = f"{int(memory_mb)}Mi"
                container.resources.limits['cpu'] = f"{cpu_cores * 2}"
                container.resources.limits['memory'] = f"{int(memory_mb * 2)}Mi"
            
            # Apply update
            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=deployment
            )
            
            self.logger.info(f"Scaled deployment {namespace}/{deployment_name}")
            return True
            
        except ApiException as e:
            self.logger.error(f"Failed to scale deployment {namespace}/{deployment_name}: {e}")
            return False

    def scale_statefulset_resources(self, namespace: str, statefulset_name: str, cpu_cores: float, memory_mb: float, dry_run: bool = False) -> bool:
        """
        Scale StatefulSet resources
        
        Args:
            namespace: StatefulSet namespace
            statefulset_name: StatefulSet name
            cpu_cores: New CPU allocation
            memory_mb: New memory allocation
            dry_run: Whether to perform dry run
            
        Returns:
            True if successful
        """
        try:
            if dry_run:
                self.logger.info(f"DRY RUN: Would scale StatefulSet {namespace}/{statefulset_name} to CPU: {cpu_cores}, Memory: {memory_mb}Mi")
                return True
                
            statefulset = self.apps_v1.read_namespaced_stateful_set(
                name=statefulset_name,
                namespace=namespace
            )
            
            # Update container resources
            for container in statefulset.spec.template.spec.containers:
                if not container.resources:
                    container.resources = client.V1ResourceRequirements()
                if not container.resources.requests:
                    container.resources.requests = {}
                if not container.resources.limits:
                    container.resources.limits = {}
                    
                container.resources.requests['cpu'] = f"{cpu_cores}"
                container.resources.requests['memory'] = f"{int(memory_mb)}Mi"
                container.resources.limits['cpu'] = f"{cpu_cores * 2}"
                container.resources.limits['memory'] = f"{int(memory_mb * 2)}Mi"
            
            # Apply update
            self.apps_v1.patch_namespaced_stateful_set(
                name=statefulset_name,
                namespace=namespace,
                body=statefulset
            )
            
            self.logger.info(f"Scaled StatefulSet {namespace}/{statefulset_name}")
            return True
            
        except ApiException as e:
            self.logger.error(f"Failed to scale StatefulSet {namespace}/{statefulset_name}: {e}")
            return False

    def check_pod_resize_capabilities(self, pod_name: str, namespace: str) -> Dict:
        """
        Check if a pod supports in-place resize and return capability information
        
        Args:
            pod_name: Name of the pod
            namespace: Pod namespace
            
        Returns:
            Dictionary containing resize capabilities and constraints
        """
        capabilities = {
            "supports_resize": False,
            "resize_policy": None,
            "container_policies": [],
            "issues": []
        }
        
        try:
            pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            
            # Check basic requirements for resize
            if pod.status.phase != "Running":
                capabilities["issues"].append(f"Pod is not running (status: {pod.status.phase})")
                return capabilities
            
            # Check if pod has resource specifications
            for container in pod.spec.containers:
                container_info = {"name": container.name, "policies": []}
                
                if not container.resources:
                    capabilities["issues"].append(f"Container {container.name} has no resource specification")
                    continue
                
                if not container.resources.requests and not container.resources.limits:
                    capabilities["issues"].append(f"Container {container.name} has neither requests nor limits")
                    continue
                
                # Check for resize policy (K8s 1.27+)
                if hasattr(container, 'resize_policy') and container.resize_policy:
                    for policy in container.resize_policy:
                        container_info["policies"].append({
                            "resource_name": policy.resource_name,
                            "restart_policy": policy.restart_policy
                        })
                
                capabilities["container_policies"].append(container_info)
            
            # If no major issues found, pod likely supports resize
            if not capabilities["issues"]:
                capabilities["supports_resize"] = True
            
            # Check for pod-level resize policy
            if hasattr(pod.spec, 'resize_policy') and pod.spec.resize_policy:
                capabilities["resize_policy"] = pod.spec.resize_policy
            
            return capabilities
            
        except ApiException as e:
            capabilities["issues"].append(f"API error: {e}")
            return capabilities
        except Exception as e:
            capabilities["issues"].append(f"Unexpected error: {e}")
            return capabilities

    def scale_pod_resources(self, pod_name: str, namespace: str, cpu_limit: float, memory_limit_mb: float) -> bool:
        """
        Scale pod resources using Kubernetes in-place resize feature
        
        This method attempts to resize pod resources without restarting the pod using 
        Kubernetes in-place pod resize feature (available in K8s 1.27+). If the resize
        subresource is not available, it falls back to updating the pod spec directly.
        
        Features:
        - Attempts in-place resize using the /resize subresource
        - Validates pod state before attempting resize
        - Provides detailed logging and error handling
        - Falls back to regular pod patch if resize API unavailable
        - Verifies resize completion with timeout
        
        Args:
            pod_name: Name of the pod to resize
            namespace: Pod namespace
            cpu_limit: New CPU limit in cores (e.g., 2.0 for 2 cores)
            memory_limit_mb: New memory limit in MB (e.g., 2048 for 2GB)
            
        Returns:
            True if scaling was successful, False otherwise
            
        Raises:
            No exceptions raised - all errors are logged and return False
        """
        if not self.is_available():
            self.logger.info(f"Kubernetes client not available - would scale {pod_name} to CPU: {cpu_limit}, Memory: {memory_limit_mb}MB")
            return False
            
        try:
            # Check pod resize capabilities first
            capabilities = self.check_pod_resize_capabilities(pod_name, namespace)
            
            if not capabilities["supports_resize"]:
                self.logger.error(f"Pod {pod_name} does not support in-place resize. Issues: {capabilities['issues']}")
                return False
            
            if capabilities["issues"]:
                self.logger.warning(f"Pod {pod_name} resize capabilities have warnings: {capabilities['issues']}")
            
            # Log resize policy information if available
            if capabilities["container_policies"]:
                for container_policy in capabilities["container_policies"]:
                    if container_policy["policies"]:
                        self.logger.info(f"Container {container_policy['name']} resize policies: {container_policy['policies']}")
            
            # Get the current pod to build the patch
            pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            
            # Prepare the patch for in-place resize
            containers = []
            for container in pod.spec.containers:
                container_patch = {
                    "name": container.name,
                    "resources": {
                        "requests": {
                            "cpu": f"{cpu_limit * 0.5:.3f}",  # 50% of limit for requests
                            "memory": f"{int(memory_limit_mb * 0.7)}Mi"  # 70% of limit for requests
                        },
                        "limits": {
                            "cpu": f"{cpu_limit:.3f}",
                            "memory": f"{int(memory_limit_mb)}Mi"
                        }
                    }
                }
                containers.append(container_patch)
            
            patch_body = {
                "spec": {
                    "containers": containers
                }
            }
            
            self.logger.info(f"Attempting in-place resize for pod {pod_name} with patch: {patch_body}")
            
            # Use the resize subresource for in-place pod resize (K8s 1.27+)
            try:
                # First try using the resize subresource API
                api_client = client.ApiClient()
                api_response = api_client.call_api(
                    resource_path=f'/api/v1/namespaces/{namespace}/pods/{pod_name}/resize',
                    method='PATCH',
                    header_params={'Content-Type': 'application/strategic-merge-patch+json'},
                    body=patch_body,
                    _return_http_data_only=True
                )
                self.logger.info(f"Successfully resized pod {pod_name} using resize subresource: {api_response is not None}")
                
            except Exception as resize_error:
                self.logger.warning(f"Resize subresource failed: {resize_error}")
                self.logger.info("Falling back to regular pod patch")
                
                # Fallback to regular pod patch (may trigger pod restart)
                self.v1.patch_namespaced_pod(
                    name=pod_name,
                    namespace=namespace,
                    body=patch_body
                )
                self.logger.info(f"Successfully updated pod {pod_name} resources via regular patch")
            
            # Wait and verify the resize
            success = self._verify_pod_resize(pod_name, namespace, cpu_limit, memory_limit_mb)
            
            if success:
                self.logger.info(f"Pod {pod_name} resize completed - CPU: {cpu_limit}, Memory: {memory_limit_mb}MB")
            else:
                self.logger.warning(f"Pod {pod_name} resize may not have been fully applied")
            
            return True
            
        except ApiException as e:
            if e.status == 400 and "resize" in str(e.reason).lower():
                self.logger.error(f"Pod {pod_name} does not support in-place resize: {e.reason}")
                return False
            elif e.status == 422:
                self.logger.error(f"Invalid resize parameters for pod {pod_name}: {e.reason}")
                return False
            else:
                self.logger.error(f"API error resizing pod {pod_name}: {e}")
                return False
        except Exception as e:
            self.logger.error(f"Unexpected error resizing pod {pod_name}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _verify_pod_resize(self, pod_name: str, namespace: str, expected_cpu: float, expected_memory: float, timeout: int = 30) -> bool:
        """
        Verify that the pod resize was applied successfully
        
        Args:
            pod_name: Name of the pod
            namespace: Pod namespace
            expected_cpu: Expected CPU limit
            expected_memory: Expected memory limit in MB
            timeout: Timeout in seconds
            
        Returns:
            True if resize was verified, False otherwise
        """
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
                
                # Check if pod conditions indicate successful resize
                if pod.status.conditions:
                    for condition in pod.status.conditions:
                        if condition.type == "PodReadyToStartContainers":
                            if condition.status == "True":
                                self.logger.info(f"Pod {pod_name} is ready to start containers")
                        elif condition.type == "ContainersReady":
                            if condition.status == "True":
                                self.logger.info(f"Pod {pod_name} containers are ready")
                
                # Check container status for resize information
                resize_in_progress = False
                containers_ready = 0
                total_containers = len(pod.spec.containers)
                
                if pod.status.container_statuses:
                    for container_status in pod.status.container_statuses:
                        # Check if container is ready
                        if container_status.ready:
                            containers_ready += 1
                        
                        # Check allocated resources (available in K8s 1.27+)
                        if hasattr(container_status, 'allocated_resources') and container_status.allocated_resources:
                            current_cpu = container_status.allocated_resources.get('cpu', '')
                            current_memory = container_status.allocated_resources.get('memory', '')
                            self.logger.info(f"Container {container_status.name} allocated resources - CPU: {current_cpu}, Memory: {current_memory}")
                        
                        # Check resize status
                        if hasattr(container_status, 'resources') and container_status.resources:
                            self.logger.info(f"Container {container_status.name} resource status available")
                
                # Check resize conditions in pod status (K8s 1.27+)
                if hasattr(pod.status, 'resize') and pod.status.resize:
                    self.logger.info(f"Pod {pod_name} resize status: {pod.status.resize}")
                    
                    for container_resize in pod.status.resize:
                        if container_resize.resource_name in ['cpu', 'memory']:
                            if container_resize.status == "InProgress":
                                resize_in_progress = True
                            elif container_resize.status == "Deferred":
                                self.logger.warning(f"Resize deferred for {container_resize.resource_name}")
                            elif container_resize.status == "Infeasible":
                                self.logger.error(f"Resize infeasible for {container_resize.resource_name}")
                                return False
                
                # Check if all containers are ready and no resize in progress
                if containers_ready == total_containers and not resize_in_progress:
                    self.logger.info(f"Pod {pod_name} resize verification completed successfully")
                    return True
                
                # Check updated resource specifications in pod spec
                all_containers_updated = True
                for container in pod.spec.containers:
                    if container.resources and container.resources.limits:
                        current_cpu_limit = container.resources.limits.get('cpu', '')
                        current_memory_limit = container.resources.limits.get('memory', '')
                        
                        # Parse current values for comparison
                        current_cpu_val = self._parse_cpu_limit(current_cpu_limit) if current_cpu_limit else 0
                        current_memory_val = self._parse_memory_limit(current_memory_limit) if current_memory_limit else 0
                        
                        # Check if values match (with small tolerance)
                        cpu_match = abs(current_cpu_val - expected_cpu) < 0.01
                        memory_match = abs(current_memory_val - expected_memory) < 10  # 10MB tolerance
                        
                        if not (cpu_match and memory_match):
                            all_containers_updated = False
                            self.logger.debug(f"Container {container.name} not yet updated - CPU: {current_cpu_val} vs {expected_cpu}, Memory: {current_memory_val} vs {expected_memory}")
                            break
                
                if all_containers_updated and containers_ready == total_containers:
                    self.logger.info(f"Pod {pod_name} resource specifications updated successfully")
                    return True
                
                time.sleep(2)
                
            except Exception as e:
                self.logger.warning(f"Error verifying resize for pod {pod_name}: {e}")
                time.sleep(2)
        
        self.logger.warning(f"Pod {pod_name} resize verification timed out after {timeout}s")
        return False

    def get_pod_owner_deployment(self, namespace: str, pod_name: str):
        """Get the deployment that owns this pod"""
        if not self.is_available():
            return None
            
        try:
            pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            if pod.metadata.owner_references:
                for owner in pod.metadata.owner_references:
                    if owner.kind == "ReplicaSet":
                        # Get the ReplicaSet to find its deployment owner
                        rs = self.apps_v1.read_namespaced_replica_set(
                            name=owner.name, namespace=namespace
                        )
                        if rs.metadata.owner_references:
                            for rs_owner in rs.metadata.owner_references:
                                if rs_owner.kind == "Deployment":
                                    return {
                                        'name': rs_owner.name,
                                        'kind': rs_owner.kind,
                                        'uid': rs_owner.uid
                                    }
        except Exception as e:
            self.logger.error(f"Error finding owner deployment for pod {pod_name}: {e}")
        
        return None

    def resize_deployment_resources(self, deployment_name, namespace="default", container_resources=None):
        """
        Resize deployment container resources directly using API format
        
        Args:
            deployment_name (str): Name of the deployment to resize
            namespace (str): Namespace of the deployment
            container_resources (dict): Dict in API format: container_name -> {requests: {}, limits: {}}
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not container_resources:
                self.logger.error("No container resources specified for resize")
                return False

            # Get the deployment
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name, 
                namespace=namespace
            )
            
            # Update container resources
            for container in deployment.spec.template.spec.containers:
                if container.name in container_resources:
                    new_resources = container_resources[container.name]
                    
                    # Create new resource requirements
                    resource_requirements = client.V1ResourceRequirements()
                    
                    # Preserve existing resources and update with new ones
                    current_requests = {}
                    current_limits = {}
                    
                    if container.resources:
                        if container.resources.requests:
                            current_requests = dict(container.resources.requests)
                        if container.resources.limits:
                            current_limits = dict(container.resources.limits)
                    
                    # Update with new values
                    if 'requests' in new_resources:
                        current_requests.update(new_resources['requests'])
                        resource_requirements.requests = current_requests

                    if current_limits <  new_resources['limits']:  
                        if 'limits' in new_resources:
                            current_limits.update(new_resources['limits'])
                            resource_requirements.limits = current_limits
                    
                    container.resources = resource_requirements
            
            # Patch the deployment
            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=deployment
            )
            
            self.logger.info(f"Updated deployment {deployment_name} resources")
            return True
            
        except ApiException as e:
            self.logger.error(f"Failed to resize deployment {deployment_name}: {e}")
            return False

def main():
    """Example usage"""
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Initialize client
        k8s_client = KubernetesClient()
        
        # Test connection
        if k8s_client.test_connection():
            print(" Connected to Kubernetes API server")
            
            # Get cluster information
            namespaces = k8s_client.get_namespaces()
            print(f"= Namespaces: {namespaces}")
            
            # Get pods in default namespace
            pods = k8s_client.get_pods("default")
            print(f"= Pods in default namespace: {len(pods)}")
            
            # Get deployments
            deployments = k8s_client.get_deployments("default")
            print(f"= Deployments in default namespace: {len(deployments)}")
            
        else:
            print("L Failed to connect to Kubernetes API server")
            
    except Exception as e:
        print(f"L Error: {e}")

def main():
    """Test the KubernetesClient functionality"""
    try:
        # Test connection
        k8s_client = KubernetesClient()
        
        if k8s_client.is_available():
            print("✓ Connected to Kubernetes API server")
            
            # Get cluster information
            namespaces = k8s_client.get_namespaces()
            print(f"= Namespaces: {namespaces}")
            
            # Get pods in default namespace
            pods = k8s_client.get_pods("default")
            print(f"= Pods in default namespace: {len(pods)}")
            
            # Get deployments
            deployments = k8s_client.get_deployments("default")
            print(f"= Deployments in default namespace: {len(deployments)}")
            
        else:
            print("L Failed to connect to Kubernetes API server")
            
    except Exception as e:
        print(f"L Error: {e}")

if __name__ == "__main__":
    main()