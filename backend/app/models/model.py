"""
机器学习模型文件模型
"""
from datetime import datetime
from app.extensions import db


class MLModel(db.Model):
    """机器学习模型表 - 存储模型文件"""
    
    __tablename__ = 'ml_models'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    model_name = db.Column(db.String(255), nullable=False, comment='模型名称')
    model_content = db.Column(db.LargeBinary, nullable=False, comment='模型文件内容（二进制）')
    model_size = db.Column(db.Integer, nullable=False, comment='模型文件大小（字节）')
    data_count = db.Column(db.Integer, nullable=False, comment='训练数据量')
    upload_time = db.Column(db.DateTime, default=datetime.now, comment='上传时间')
    description = db.Column(db.Text, comment='模型描述')
    model_type = db.Column(db.String(100), comment='模型类型（如sklearn, pytorch等）')
    
    def __repr__(self):
        return f'<MLModel {self.model_name}>'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'model_name': self.model_name,
            'model_size': self.model_size,
            'data_count': self.data_count,
            'upload_time': self.upload_time.strftime('%Y-%m-%d %H:%M:%S') if self.upload_time else None,
            'description': self.description,
            'model_type': self.model_type
        }
    
    @staticmethod
    def save_model(model_name, model_content, data_count, description=None, model_type=None):
        """
        保存模型文件到数据库
        
        Args:
            model_name: 模型名称
            model_content: 模型文件的二进制内容
            data_count: 训练数据量
            description: 模型描述
            model_type: 模型类型
            
        Returns:
            MLModel对象
        """
        ml_model = MLModel(
            model_name=model_name,
            model_content=model_content,
            model_size=len(model_content),
            data_count=data_count,
            description=description,
            model_type=model_type
        )
        db.session.add(ml_model)
        db.session.commit()
        return ml_model
    
    def get_model_content(self):
        """
        获取模型文件的原始内容
        
        Returns:
            bytes: 模型文件的二进制内容
        """
        return self.model_content

