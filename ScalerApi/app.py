from flask import Flask
from flask_cors import CORS
import logging
from core_functions import ApplicationCore, setup_logging, print_startup_info
from api_routes import register_routes

setup_logging()
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    CORS(app)
    app_core = ApplicationCore()
    config = app_core.get_config()
    print_startup_info(config)
    scaling_service = app_core.initialize()
    register_routes(app, scaling_service, config, app_core)
    return app, app_core, scaling_service


def main():
    try:
        app, app_core, scaling_service = create_app()
        logger.info("Starting Flask application on port 5404...")
        app.run(host='0.0.0.0', port=5404, debug=False, threaded=True)
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        raise
    finally:
        # Cleanup
        if 'app_core' in locals():
            app_core.stop_auto_scaler()
        logger.info("Application shutdown complete")


# Create app instance for gunicorn
app, app_core, scaling_service = create_app()

if __name__ == '__main__':
    main()