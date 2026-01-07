"""
机器学习模型操作路由
"""
from flask import Blueprint, request, jsonify, send_file
from app.models.model import MLModel
from app.extensions import db
import io

model_bp = Blueprint('model', __name__, url_prefix='/api/models')


@model_bp.route('/', methods=['POST'])
def upload_model():
    """
    上传模型文件
    
    请求参数:
        - file: 模型文件（multipart/form-data）
        - model_name: 模型名称
        - data_count: 训练数据量（整数）
        - description: 模型描述（可选）
        - model_type: 模型类型（可选，如sklearn, pytorch等）
    """
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({'error': '未上传文件'}), 400
        
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400
        
        # 获取模型名称和数据量
        model_name = request.form.get('model_name', file.filename)
        data_count = request.form.get('data_count', type=int)
        
        if data_count is None:
            return jsonify({'error': '必须提供训练数据量(data_count)'}), 400
        
        if data_count < 0:
            return jsonify({'error': '训练数据量必须为正整数'}), 400
        
        # 读取文件内容
        file_content = file.read()
        description = request.form.get('description', '')
        model_type = request.form.get('model_type', '')
        
        # 保存到数据库
        ml_model = MLModel.save_model(
            model_name=model_name,
            model_content=file_content,
            data_count=data_count,
            description=description,
            model_type=model_type
        )
        
        return jsonify({
            'message': '模型上传成功',
            'data': ml_model.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'上传失败: {str(e)}'}), 500


@model_bp.route('/', methods=['GET'])
def get_models():
    """获取所有模型列表"""
    try:
        models = MLModel.query.order_by(MLModel.upload_time.desc()).all()
        return jsonify({
            'message': '获取成功',
            'data': [m.to_dict() for m in models],
            'total': len(models)
        }), 200
    except Exception as e:
        return jsonify({'error': f'获取失败: {str(e)}'}), 500


@model_bp.route('/<int:model_id>', methods=['GET'])
def get_model(model_id):
    """获取指定ID的模型信息"""
    try:
        ml_model = MLModel.query.get(model_id)
        if not ml_model:
            return jsonify({'error': '模型不存在'}), 404
        
        return jsonify({
            'message': '获取成功',
            'data': ml_model.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'error': f'获取失败: {str(e)}'}), 500


@model_bp.route('/<int:model_id>/download', methods=['GET'])
def download_model(model_id):
    """下载模型文件"""
    try:
        ml_model = MLModel.query.get(model_id)
        if not ml_model:
            return jsonify({'error': '模型不存在'}), 404
        
        # 创建BytesIO对象
        file_buffer = io.BytesIO(ml_model.get_model_content())
        file_buffer.seek(0)
        
        return send_file(
            file_buffer,
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=ml_model.model_name
        )
    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'}), 500


@model_bp.route('/<int:model_id>', methods=['PUT'])
def update_model(model_id):
    """
    更新模型信息（不包括文件内容）
    
    请求参数（JSON）:
        - model_name: 模型名称（可选）
        - data_count: 训练数据量（可选）
        - description: 模型描述（可选）
        - model_type: 模型类型（可选）
    """
    try:
        ml_model = MLModel.query.get(model_id)
        if not ml_model:
            return jsonify({'error': '模型不存在'}), 404
        
        data = request.get_json()
        
        # 更新字段
        if 'model_name' in data:
            ml_model.model_name = data['model_name']
        if 'data_count' in data:
            if data['data_count'] < 0:
                return jsonify({'error': '训练数据量必须为正整数'}), 400
            ml_model.data_count = data['data_count']
        if 'description' in data:
            ml_model.description = data['description']
        if 'model_type' in data:
            ml_model.model_type = data['model_type']
        
        db.session.commit()
        
        return jsonify({
            'message': '模型信息更新成功',
            'data': ml_model.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'更新失败: {str(e)}'}), 500


@model_bp.route('/<int:model_id>', methods=['DELETE'])
def delete_model(model_id):
    """删除模型"""
    try:
        ml_model = MLModel.query.get(model_id)
        if not ml_model:
            return jsonify({'error': '模型不存在'}), 404
        
        model_name = ml_model.model_name
        db.session.delete(ml_model)
        db.session.commit()
        
        return jsonify({
            'message': f'模型 {model_name} 删除成功'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'删除失败: {str(e)}'}), 500

