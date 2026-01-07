"""
数据文件操作路由
"""
from flask import Blueprint, request, jsonify, send_file
from app.models.datafile import DataFile
from app.extensions import db
import io

datafile_bp = Blueprint('datafile', __name__, url_prefix='/api/datafiles')


@datafile_bp.route('/', methods=['POST'])
def upload_datafile():
    """
    上传CSV文件
    
    请求参数:
        - file: CSV文件（multipart/form-data）
        - description: 文件描述（可选）
    """
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({'error': '未上传文件'}), 400
        
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400
        
        # 检查文件扩展名
        if not file.filename.endswith('.csv'):
            return jsonify({'error': '只支持CSV文件'}), 400
        
        # 读取文件内容
        file_content = file.read()
        description = request.form.get('description', '')
        
        # 保存到数据库
        datafile = DataFile.save_csv(
            filename=file.filename,
            csv_content=file_content,
            description=description
        )
        
        return jsonify({
            'message': '文件上传成功',
            'data': datafile.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'上传失败: {str(e)}'}), 500


@datafile_bp.route('/', methods=['GET'])
def get_datafiles():
    """获取所有数据文件列表"""
    try:
        datafiles = DataFile.query.order_by(DataFile.upload_time.desc()).all()
        return jsonify({
            'message': '获取成功',
            'data': [df.to_dict() for df in datafiles],
            'total': len(datafiles)
        }), 200
    except Exception as e:
        return jsonify({'error': f'获取失败: {str(e)}'}), 500


@datafile_bp.route('/<int:file_id>', methods=['GET'])
def get_datafile(file_id):
    """获取指定ID的数据文件信息"""
    try:
        datafile = DataFile.query.get(file_id)
        if not datafile:
            return jsonify({'error': '文件不存在'}), 404
        
        return jsonify({
            'message': '获取成功',
            'data': datafile.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'error': f'获取失败: {str(e)}'}), 500


@datafile_bp.route('/<int:file_id>/download', methods=['GET'])
def download_datafile(file_id):
    """下载CSV文件"""
    try:
        datafile = DataFile.query.get(file_id)
        if not datafile:
            return jsonify({'error': '文件不存在'}), 404
        
        # 创建BytesIO对象
        file_buffer = io.BytesIO(datafile.get_csv_content())
        file_buffer.seek(0)
        
        return send_file(
            file_buffer,
            mimetype='text/csv',
            as_attachment=True,
            download_name=datafile.filename
        )
    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'}), 500


@datafile_bp.route('/<int:file_id>/preview', methods=['GET'])
def preview_datafile(file_id):
    """
    预览CSV文件内容（返回前10行）
    
    可选参数:
        - rows: 返回的行数（默认10）
    """
    try:
        datafile = DataFile.query.get(file_id)
        if not datafile:
            return jsonify({'error': '文件不存在'}), 404
        
        # 转换为DataFrame
        df = datafile.to_dataframe()
        
        # 获取预览行数
        rows = request.args.get('rows', 10, type=int)
        rows = min(rows, 100)  # 最多100行
        
        # 转换为JSON格式
        preview_data = df.head(rows).to_dict(orient='records')
        
        return jsonify({
            'message': '预览成功',
            'data': {
                'filename': datafile.filename,
                'total_rows': len(df),
                'columns': list(df.columns),
                'preview_rows': rows,
                'preview_data': preview_data
            }
        }), 200
    except Exception as e:
        return jsonify({'error': f'预览失败: {str(e)}'}), 500


@datafile_bp.route('/<int:file_id>', methods=['DELETE'])
def delete_datafile(file_id):
    """删除数据文件"""
    try:
        datafile = DataFile.query.get(file_id)
        if not datafile:
            return jsonify({'error': '文件不存在'}), 404
        
        filename = datafile.filename
        db.session.delete(datafile)
        db.session.commit()
        
        return jsonify({
            'message': f'文件 {filename} 删除成功'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'删除失败: {str(e)}'}), 500

