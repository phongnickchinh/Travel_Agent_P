"""Health check controller."""

from flask import Blueprint, jsonify

def init_app():
    """Initialize health check blueprint."""
    health_api = Blueprint('health', __name__)

    @health_api.route('/health', methods=['GET'])
    def health_check():
        """
        Health check endpoint.
        Returns a 200 OK response when the server is running properly.
        This endpoint is used by Render.com to determine if the service is healthy.
        """
        return jsonify({"status": "ok", "message": "Server is running"}), 200

    return health_api
