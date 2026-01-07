"""
数据库初始化脚本
"""
from app import create_app
from app.extensions import db
from app.models import DataFile, MLModel, Client

def init_database():
    """初始化数据库，创建所有表"""
    app = create_app()
    
    with app.app_context():
        # 创建所有表
        db.create_all()
        print("✅ 数据库表创建成功！")
        print(f"   - {DataFile.__tablename__}: 数据文件表")
        print(f"   - {MLModel.__tablename__}: 机器学习模型表")
        print(f"   - {Client.__tablename__}: 客户端表")

if __name__ == '__main__':
    init_database()

