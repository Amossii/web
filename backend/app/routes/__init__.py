"""
路由模块初始化
"""
from app.routes.health import health_bp
from app.routes.datafile import datafile_bp
from app.routes.model import model_bp
from app.routes.client import client_bp
from app.routes.agent import agent_bp

__all__ = ['health_bp', 'datafile_bp', 'model_bp', 'client_bp', 'agent_bp']

