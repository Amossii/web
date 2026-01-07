"""
Flask 应用工厂
"""
from flask import Flask
from app.config import Config
from app.extensions import db


def create_app(config_class=Config):
    """
    创建并配置 Flask 应用实例
    
    Args:
        config_class: 配置类
        
    Returns:
        Flask 应用实例
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 初始化扩展
    db.init_app(app)
    
    # 注册蓝图
    from app.routes import health_bp, datafile_bp, model_bp, client_bp, agent_bp
    app.register_blueprint(health_bp)
    app.register_blueprint(datafile_bp)
    app.register_blueprint(model_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(agent_bp)
    
    return app

