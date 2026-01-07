"""
客户端模型 - 关联数据文件和模型文件
"""
from datetime import datetime
from app.extensions import db


class Client(db.Model):
    """客户端表 - 关联数据文件和模型"""
    
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False, comment='客户端名称')
    
    # 关联数据文件（外键，可为空）
    datafile_id = db.Column(db.Integer, db.ForeignKey('datafiles.id'), nullable=True, comment='关联的数据文件ID')
    
    # 关联模型文件（外键，可为空）
    model_id = db.Column(db.Integer, db.ForeignKey('ml_models.id'), nullable=True, comment='关联的模型ID')
    
    created_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    description = db.Column(db.Text, comment='客户端描述')
    
    # 建立关系
    datafile = db.relationship('DataFile', backref='clients', foreign_keys=[datafile_id])
    model = db.relationship('MLModel', backref='clients', foreign_keys=[model_id])
    
    def __repr__(self):
        return f'<Client {self.name}>'
    
    def to_dict(self):
        """转换为字典格式"""
        result = {
            'id': self.id,
            'name': self.name,
            'datafile_id': self.datafile_id,
            'model_id': self.model_id,
            'created_time': self.created_time.strftime('%Y-%m-%d %H:%M:%S') if self.created_time else None,
            'updated_time': self.updated_time.strftime('%Y-%m-%d %H:%M:%S') if self.updated_time else None,
            'description': self.description
        }
        
        # 如果有关联的数据文件，添加其信息
        if self.datafile:
            result['datafile_info'] = {
                'id': self.datafile.id,
                'filename': self.datafile.filename,
                'file_size': self.datafile.file_size
            }
        
        # 如果有关联的模型，添加其信息
        if self.model:
            result['model_info'] = {
                'id': self.model.id,
                'model_name': self.model.model_name,
                'data_count': self.model.data_count,
                'model_type': self.model.model_type
            }
        
        return result
    
    @staticmethod
    def create_client(name, description=None):
        """
        创建新的客户端
        
        Args:
            name: 客户端名称
            description: 描述
            
        Returns:
            Client对象
        """
        client = Client(
            name=name,
            description=description
        )
        db.session.add(client)
        db.session.commit()
        return client
    
    def bind_datafile(self, datafile_id):
        """绑定数据文件"""
        self.datafile_id = datafile_id
        self.updated_time = datetime.now()
        db.session.commit()
    
    def bind_model(self, model_id):
        """绑定模型文件"""
        self.model_id = model_id
        self.updated_time = datetime.now()
        db.session.commit()
    
    def unbind_datafile(self):
        """解绑数据文件"""
        self.datafile_id = None
        self.updated_time = datetime.now()
        db.session.commit()
    
    def unbind_model(self):
        """解绑模型"""
        self.model_id = None
        self.updated_time = datetime.now()
        db.session.commit()

