#!/usr/bin/env python3
import os
import time
import json
import logging
from datetime import datetime
from kubernetes import client, config
import redis
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MetricsCollector:
    def __init__(self):
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes config")
        except:
            config.load_kube_config()
            logger.info("Loaded local Kubernetes config")

        self.v1 = client.CoreV1Api()
        self.custom_api = client.CustomObjectsApi()

        redis_host = os.getenv('REDIS_HOST', 'redis')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_db = int(os.getenv('REDIS_DB', '0'))

        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True
        )
        logger.info(f"Connected to Redis at {redis_host}:{redis_port}")

        self.collection_interval = int(os.getenv('COLLECTION_INTERVAL', '30'))
        self.namespace = os.getenv('NAMESPACE', 'default')

    def get_pod_metrics(self):
        """Fetch pod metrics from Kubernetes metrics API"""
        try:
            metrics = self.custom_api.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=self.namespace,
                plural="pods"
            )
            return metrics.get('items', [])
        except Exception as e:
            logger.error(f"Error fetching pod metrics: {e}")
            return []

    def get_pod_info(self):
        """Get pod information including IP addresses"""
        try:
            pods = self.v1.list_namespaced_pod(namespace=self.namespace)
            pod_info = {}
            for pod in pods.items:
                pod_name = pod.metadata.name
                pod_info[pod_name] = {
                    'ip': pod.status.pod_ip,
                    'phase': pod.status.phase,
                    'node': pod.spec.node_name,
                    'namespace': pod.metadata.namespace
                }
            return pod_info
        except Exception as e:
            logger.error(f"Error fetching pod info: {e}")
            return {}

    def measure_network_latency(self, pod_ip, pod_name):
        """Measure network latency to a pod"""
        if not pod_ip:
            return None

        try:
            start_time = time.time()
            response = requests.get(f"http://{pod_ip}", timeout=2)
            latency = (time.time() - start_time) * 1000
            return round(latency, 2)
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout measuring latency for {pod_name}")
            return None
        except Exception as e:
            logger.debug(f"Could not measure latency for {pod_name}: {e}")
            return None

    def parse_resource_value(self, value):
        """Parse Kubernetes resource values (e.g., '100m', '128Mi')"""
        if not value:
            return 0

        value = str(value)
        if value.endswith('n'):
            return float(value[:-1]) / 1e9
        elif value.endswith('u'):
            return float(value[:-1]) / 1e6
        elif value.endswith('m'):
            return float(value[:-1]) / 1000
        elif value.endswith('Ki'):
            return float(value[:-2]) * 1024
        elif value.endswith('Mi'):
            return float(value[:-2]) * 1024 * 1024
        elif value.endswith('Gi'):
            return float(value[:-2]) * 1024 * 1024 * 1024
        else:
            try:
                return float(value)
            except:
                return 0

    def collect_and_store_metrics(self):
        """Main collection loop"""
        timestamp = datetime.utcnow().isoformat()

        pod_metrics = self.get_pod_metrics()
        pod_info = self.get_pod_info()

        logger.info(f"Collecting metrics for {len(pod_metrics)} pods")

        for metric in pod_metrics:
            try:
                pod_name = metric['metadata']['name']
                containers = metric.get('containers', [])

                info = pod_info.get(pod_name, {})
                pod_ip = info.get('ip')

                total_cpu = 0
                total_memory = 0

                for container in containers:
                    cpu_usage = self.parse_resource_value(container['usage'].get('cpu', '0'))
                    memory_usage = self.parse_resource_value(container['usage'].get('memory', '0'))

                    total_cpu += cpu_usage
                    total_memory += memory_usage

                network_latency = self.measure_network_latency(pod_ip, pod_name)

                metrics_data = {
                    'timestamp': timestamp,
                    'pod_name': pod_name,
                    'namespace': self.namespace,
                    'node': info.get('node', 'unknown'),
                    'pod_ip': pod_ip,
                    'phase': info.get('phase', 'unknown'),
                    'cpu_usage': round(total_cpu, 6),
                    'cpu_usage_cores': round(total_cpu, 6),
                    'memory_usage': int(total_memory),
                    'memory_usage_mb': round(total_memory / (1024 * 1024), 2),
                    'network_latency_ms': network_latency,
                    'container_count': len(containers)
                }

                redis_key = f"pod_metrics:{self.namespace}:{pod_name}:{timestamp}"
                self.redis_client.setex(
                    redis_key,
                    86400,
                    json.dumps(metrics_data)
                )

                latest_key = f"pod_metrics:latest:{self.namespace}:{pod_name}"
                self.redis_client.setex(
                    latest_key,
                    86400,
                    json.dumps(metrics_data)
                )

                logger.info(f"Stored metrics for {pod_name}: CPU={metrics_data['cpu_usage_cores']}, "
                           f"Memory={metrics_data['memory_usage_mb']}MB, Latency={network_latency}ms")

            except Exception as e:
                logger.error(f"Error processing metrics for pod: {e}")

    def run(self):
        """Main run loop"""
        logger.info(f"Starting metrics collector (interval: {self.collection_interval}s, namespace: {self.namespace})")

        while True:
            try:
                self.collect_and_store_metrics()
            except Exception as e:
                logger.error(f"Error in collection cycle: {e}")

            logger.info(f"Waiting {self.collection_interval} seconds until next collection...")
            time.sleep(self.collection_interval)

if __name__ == "__main__":
    collector = MetricsCollector()
    collector.run()
