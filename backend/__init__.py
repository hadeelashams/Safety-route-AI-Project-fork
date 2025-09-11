# backend/__init__.py

from flask import Blueprint

# Blueprint for authentication routes (login, signup, logout)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Blueprint for main user-facing views (dashboard, landing page)
views_bp = Blueprint('views', __name__)

# Blueprint for all admin-related functions
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Blueprint for the AI service API
# (This is already in aiservice.py, but defining here is good practice for consistency)
ai_bp = Blueprint('ai_service', __name__)