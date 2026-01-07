"""
数据文件模型
"""
from datetime import datetime
from app.extensions import db
import io
import pandas as pd


class DataFile(db.Model):
    """数据文件表 - 存储CSV文件"""
    
    __tablename__ = 'datafiles'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    filename = db.Column(db.String(255), nullable=False, comment='文件名')
    file_content = db.Column(db.LargeBinary, nullable=False, comment='文件内容（二进制）')
    file_size = db.Column(db.Integer, nullable=False, comment='文件大小（字节）')
    upload_time = db.Column(db.DateTime, default=datetime.now, comment='上传时间')
    description = db.Column(db.Text, comment='文件描述')
    
    def __repr__(self):
        return f'<DataFile {self.filename}>'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'filename': self.filename,
            'file_size': self.file_size,
            'upload_time': self.upload_time.strftime('%Y-%m-%d %H:%M:%S') if self.upload_time else None,
            'description': self.description
        }
    
    @staticmethod
    def save_csv(filename, csv_content, description=None):
        """
        保存CSV文件到数据库
        
        Args:
            filename: 文件名
            csv_content: CSV文件的二进制内容
            description: 文件描述
            
        Returns:
            DataFile对象
        """
        datafile = DataFile(
            filename=filename,
            file_content=csv_content,
            file_size=len(csv_content),
            description=description
        )
        db.session.add(datafile)
        db.session.commit()
        return datafile
    
    def to_dataframe(self):
        """
        将存储的CSV文件转换为pandas DataFrame
        
        Returns:
            pandas.DataFrame
        """
        try:
            # 将二进制内容转换为BytesIO对象
            csv_buffer = io.BytesIO(self.file_content)
            # 读取为DataFrame
            df = pd.read_csv(csv_buffer, encoding='utf-8')
            return df
        except Exception as e:
            # 尝试其他编码
            try:
                csv_buffer = io.BytesIO(self.file_content)
                df = pd.read_csv(csv_buffer, encoding='gbk')
                return df
            except:
                raise Exception(f"无法解析CSV文件: {str(e)}")
    
    def get_csv_content(self):
        """
        获取CSV文件的原始内容
        
        Returns:
            bytes: CSV文件的二进制内容
        """
        return self.file_content

