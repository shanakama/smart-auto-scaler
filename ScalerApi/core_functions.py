import logging
import time
from threading import Thread, Lock
from scaling_service import ScalingService

logger = logging.getLogger(__name__)

class AutoScalerManager:
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.scaling_service = None
        self.auto_scaler_thread = None
        self.auto_scaler_running = False
        self.auto_scaler_lock = Lock()
        
    def get_current_config(self):
        """Get the current live configuration"""
        return self.config_manager.get_config()
        
    def initialize_service(self):
        try:
            self.scaling_service = ScalingService(self.get_current_config())
            logger.info("Scaling service initialized successfully")
            return self.scaling_service
        except Exception as e:
            logger.error(f"Failed to initialize scaling service: {e}")
            raise

    def auto_scaler_loop(self):
        logger.info("Auto-scaler thread started")

        while self.auto_scaler_running:
            try:
                current_config = self.get_current_config()
                logger.info(f"Auto-scaler thread started (enabled: {current_config['auto_scale_enabled']}, interval: {current_config['auto_scale_interval']}s)")
                
                if current_config['auto_scale_enabled']:
                    logger.info("Running automatic scaling cycle...")
                    results = self.scaling_service.process_all_pods()
                    logger.info(f"Auto-scaling complete. Processed {len(results)} pods")    
                else:
                    logger.info("Auto-scaling disabled, skipping cycle")

                # Sleep for configured interval
                logger.debug(f"Sleeping for {current_config['auto_scale_interval']} seconds...")
                time.sleep(current_config['auto_scale_interval'])
            except Exception as e:
                logger.error(f"Error in auto-scaler loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

        logger.info("Auto-scaler thread stopped")

    def start_auto_scaler(self):
        with self.auto_scaler_lock:
            if self.auto_scaler_thread is None or not self.auto_scaler_thread.is_alive():
                self.auto_scaler_running = True
                self.auto_scaler_thread = Thread(target=self.auto_scaler_loop, daemon=True)
                self.auto_scaler_thread.start()
                current_config = self.get_current_config()
                logger.info(f"Auto-scaler thread started (enabled: {current_config['auto_scale_enabled']}, interval: {current_config['auto_scale_interval']}s)")
            else:
                logger.info("Auto-scaler thread already running")

    def stop_auto_scaler(self):
        with self.auto_scaler_lock:
            self.auto_scaler_running = False
            logger.info("Auto-scaler stopped")

    def is_auto_scaler_running(self):
        return self.auto_scaler_running

    def is_auto_scaler_thread_alive(self):
        return self.auto_scaler_thread.is_alive() if self.auto_scaler_thread else False

    def get_scaling_service(self):
        return self.scaling_service


class ConfigManager:
    
    def __init__(self):
        self.config = self._get_default_config()
    
    def _get_default_config(self):
        import os
        return {
            'model_path': os.path.join(os.path.dirname(__file__), 'final-models', 'dqn_model.pth'),
            'state_dim': 8,
            'action_dim': 3,
            'history_window': 5,
            'min_cpu': 0.1,
            'max_cpu': 8.0,
            'min_memory': 20,
            'max_memory': 16384,
            'scale_factor': 0.2,
            'dry_run': True, 
            'in_cluster': False,  # Set to True when running inside Kubernetes
            'namespaces': ['default'],
            'auto_scale_enabled': True,
            'auto_scale_interval': 30,  
            'scaling_cooldown': 30,
            'excluded_deployments': ['redis', 'dqn-scaler', 'metrics-collector', 'load-generator', 'dqn-scaler-dashboard'],
            'excluded_labels': {'app': 'redis', 'component': 'redis'} 
        }
    
    def get_config(self):
        return self.config
    
    def update_config(self, updates):
        for key, value in updates.items():
            if key in self.config:
                self.config[key] = value
                logger.info(f"Updated config: {key} = {value}")


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def print_startup_info(config):
    logger.info("="*70)
    logger.info(f"Auto Scale Enabled: {config['auto_scale_enabled']}")
    logger.info(f"Auto Scale Enabled: {config['in_cluster']}")
    logger.info("="*70)


class ApplicationCore:
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.auto_scaler_manager = AutoScalerManager(self.config_manager)
        
    def initialize(self):
        scaling_service = self.auto_scaler_manager.initialize_service()
        self.auto_scaler_manager.start_auto_scaler()
        return scaling_service
    
    def get_config(self):
        return self.config_manager.get_config()
    
    def update_config(self, updates):
        return self.config_manager.update_config(updates)
    
    def get_auto_scaler_manager(self):
        return self.auto_scaler_manager
    
    def start_auto_scaler(self):
        return self.auto_scaler_manager.start_auto_scaler()
    
    def stop_auto_scaler(self):
        return self.auto_scaler_manager.stop_auto_scaler()
    
    def is_auto_scaler_running(self):
        return self.auto_scaler_manager.is_auto_scaler_running()
    
    def is_auto_scaler_thread_alive(self):
        return self.auto_scaler_manager.is_auto_scaler_thread_alive()