"""
客户端操作路由
"""
from flask import Blueprint, request, jsonify
from app.models.client import Client
from app.models.datafile import DataFile
from app.models.model import MLModel
from app.extensions import db
import pickle
import io

client_bp = Blueprint('client', __name__, url_prefix='/api/clients')


@client_bp.route('/', methods=['POST'])
def create_client():
    """
    创建新的客户端
    
    请求参数 (JSON):
        - name: 客户端名称（必需）
        - description: 描述（可选）
    """
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({'error': '必须提供客户端名称(name)'}), 400
        
        name = data['name']
        description = data.get('description', '')
        
        # 创建客户端
        client = Client.create_client(name=name, description=description)
        
        return jsonify({
            'message': '客户端创建成功',
            'data': client.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'创建失败: {str(e)}'}), 500


@client_bp.route('/', methods=['GET'])
def get_clients():
    """获取所有客户端列表"""
    try:
        clients = Client.query.order_by(Client.created_time.desc()).all()
        return jsonify({
            'message': '获取成功',
            'data': [c.to_dict() for c in clients],
            'total': len(clients)
        }), 200
    except Exception as e:
        return jsonify({'error': f'获取失败: {str(e)}'}), 500


@client_bp.route('/<int:client_id>', methods=['GET'])
def get_client(client_id):
    """获取指定ID的客户端信息"""
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': '客户端不存在'}), 404
        
        return jsonify({
            'message': '获取成功',
            'data': client.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'error': f'获取失败: {str(e)}'}), 500


@client_bp.route('/<int:client_id>', methods=['DELETE'])
def delete_client(client_id):
    """删除客户端"""
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': '客户端不存在'}), 404
        
        client_name = client.name
        db.session.delete(client)
        db.session.commit()
        
        return jsonify({
            'message': f'客户端 {client_name} 删除成功'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'删除失败: {str(e)}'}), 500


@client_bp.route('/<int:client_id>/bind-datafile', methods=['POST'])
def bind_datafile(client_id):
    """
    绑定数据文件到客户端
    
    请求参数 (JSON):
        - datafile_id: 数据文件ID（必需）
    """
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': '客户端不存在'}), 404
        
        data = request.get_json()
        if not data or 'datafile_id' not in data:
            return jsonify({'error': '必须提供数据文件ID(datafile_id)'}), 400
        
        datafile_id = data['datafile_id']
        
        # 检查数据文件是否存在
        datafile = DataFile.query.get(datafile_id)
        if not datafile:
            return jsonify({'error': '数据文件不存在'}), 404
        
        # 绑定数据文件
        client.bind_datafile(datafile_id)
        
        return jsonify({
            'message': '数据文件绑定成功',
            'data': client.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'绑定失败: {str(e)}'}), 500


@client_bp.route('/<int:client_id>/unbind-datafile', methods=['POST'])
def unbind_datafile(client_id):
    """解绑客户端的数据文件"""
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': '客户端不存在'}), 404
        
        if not client.datafile_id:
            return jsonify({'error': '该客户端未绑定数据文件'}), 400
        
        client.unbind_datafile()
        
        return jsonify({
            'message': '数据文件解绑成功',
            'data': client.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'解绑失败: {str(e)}'}), 500


@client_bp.route('/<int:client_id>/bind-model', methods=['POST'])
def bind_model(client_id):
    """
    绑定模型到客户端
    
    请求参数 (JSON):
        - model_id: 模型ID（必需）
    """
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': '客户端不存在'}), 404
        
        data = request.get_json()
        if not data or 'model_id' not in data:
            return jsonify({'error': '必须提供模型ID(model_id)'}), 400
        
        model_id = data['model_id']
        
        # 检查模型是否存在
        model = MLModel.query.get(model_id)
        if not model:
            return jsonify({'error': '模型不存在'}), 404
        
        # 绑定模型
        client.bind_model(model_id)
        
        return jsonify({
            'message': '模型绑定成功',
            'data': client.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'绑定失败: {str(e)}'}), 500


@client_bp.route('/<int:client_id>/unbind-model', methods=['POST'])
def unbind_model(client_id):
    """解绑客户端的模型"""
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': '客户端不存在'}), 404
        
        if not client.model_id:
            return jsonify({'error': '该客户端未绑定模型'}), 400
        
        client.unbind_model()
        
        return jsonify({
            'message': '模型解绑成功',
            'data': client.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'解绑失败: {str(e)}'}), 500


@client_bp.route('/<int:client_id>/train', methods=['POST'])
def train_client(client_id):
    """
    训练客户端（使用绑定的数据文件进行训练）
    
    请求参数 (JSON):
        - model_name: 训练后保存的模型名称（可选，默认为 "client_{id}_model"）
        - model_type: 模型类型（可选，默认为 "lightgbm"）
        - description: 模型描述（可选）
    """
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': '客户端不存在'}), 404
        
        # 检查是否绑定了数据文件
        if not client.datafile_id:
            return jsonify({'error': '该客户端未绑定数据文件，无法训练'}), 400
        
        # 获取数据文件
        datafile = DataFile.query.get(client.datafile_id)
        if not datafile:
            return jsonify({'error': '关联的数据文件不存在'}), 404
        
        # 1. 从数据库读取 CSV 并转换为 DataFrame
        try:
            df = datafile.to_dataframe()
            print(f"成功读取数据文件: {datafile.filename}, 行数: {len(df)}")
        except Exception as e:
            return jsonify({'error': f'读取CSV文件失败: {str(e)}'}), 500
        
        # 2. 数据预处理
        try:
            from app.train.data_load import preprocess_df
            processed_df = preprocess_df(df, is_train=True)
            print(f"数据预处理完成，处理后行数: {len(processed_df)}")
        except Exception as e:
            return jsonify({'error': f'数据预处理失败: {str(e)}'}), 500
        
        # 3. 训练模型
        try:
            from app.train.train_dp import train_model
            model = train_model(processed_df)
            print(f"模型训练完成")
        except Exception as e:
            return jsonify({'error': f'模型训练失败: {str(e)}'}), 500
        
        # 4. 保存模型到数据库
        try:
            # 序列化模型
            model_bytes = pickle.dumps(model)
            
            # 获取请求参数
            data = request.get_json() or {}
            model_name = data.get('model_name', f'client_{client_id}_model')
            model_type = data.get('model_type', 'lightgbm')
            description = data.get('description', f'由客户端 {client.name} 训练生成')
            
            # 保存模型
            ml_model = MLModel.save_model(
                model_name=model_name,
                model_content=model_bytes,
                data_count=len(df),
                description=description,
                model_type=model_type
            )
            
            # 自动绑定模型到客户端
            client.bind_model(ml_model.id)
            
            print(f"模型保存成功，ID: {ml_model.id}")
            
        except Exception as e:
            return jsonify({'error': f'保存模型失败: {str(e)}'}), 500
        
        return jsonify({
            'message': '训练完成并保存成功',
            'data': {
                'client': client.to_dict(),
                'model': ml_model.to_dict(),
                'training_info': {
                    'data_rows': len(df),
                    'processed_rows': len(processed_df)
                }
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'训练失败: {str(e)}'}), 500


@client_bp.route('/evaluate', methods=['POST'])
def evaluate_clients():
    from  app.train.train_dp import eval_house_by_dict
    from  app.train.eval import federated_predict_house
    """
    评测接口 - 使用多个客户端的模型进行预测
    
    请求参数 (JSON):
        - client_ids: 客户端ID列表（必需）
        - house_data: 房屋数据（dict格式，必需）
        
    示例:
    {
        "client_ids": [1, 2],
        "house_data": {
            "城市": "大连",
            "区域": "高新园区",
            "街道": "凌水",
            "小区": "大有恬园公寓",
            "建筑面积": 35.72,
            ...
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': '请求体不能为空'}), 400
        
        if 'client_ids' not in data:
            return jsonify({'error': '必须提供客户端ID列表(client_ids)'}), 400
        
        if 'house_data' not in data:
            return jsonify({'error': '必须提供房屋数据(house_data)'}), 400
        
        client_ids = data['client_ids']
        house_data = data['house_data']
        
        if not isinstance(client_ids, list) or len(client_ids) == 0:
            return jsonify({'error': 'client_ids 必须是非空列表'}), 400
        
        if not isinstance(house_data, dict):
            return jsonify({'error': 'house_data 必须是字典格式'}), 400
        
        # 获取所有指定的客户端
        clients = Client.query.filter(Client.id.in_(client_ids)).all()
        
        if len(clients) == 0:
            return jsonify({'error': '未找到指定的客户端'}), 404
        
        results = []
        
        for client in clients:
            result = {
                'client_id': client.id,
                'client_name': client.name,
                'status': None,
                'prediction': None,
                'error': None
            }
            
            # 检查是否绑定了模型
            if not client.model_id:
                result['status'] = 'skipped'
                result['error'] = '该客户端未绑定模型'
                results.append(result)
                continue
            
            # 获取模型
            model_obj = MLModel.query.get(client.model_id)
            if not model_obj:
                result['status'] = 'error'
                result['error'] = '关联的模型不存在'
                results.append(result)
                continue
            
            try:
                # 1. 加载模型
                model_bytes = model_obj.get_model_content()
                model = pickle.loads(model_bytes)


                # 2. 构建特征（这里简化处理，实际可能需要调用 build_house_features）
                # 暂时返回一个占位符结果
                # TODO: 集成 others.py 的 build_house_features 函数
                unit_price, total_price = eval_house_by_dict(house_data, model)

                # 临时方案：返回模型信息和数据信息
                result['status'] = 'success'
                result['prediction'] = {
                    'model_name': model_obj.model_name,
                    'data_count': model_obj.data_count,
                    'model_type': model_obj.model_type,
                    "unit_price": unit_price,
                    "total_price": total_price

                }
                
            except Exception as e:
                result['status'] = 'error'
                result['error'] = f'预测失败: {str(e)}'
            
            results.append(result)
        
        # 统计结果
        success_count = sum(1 for r in results if r['status'] == 'success')
        error_count = sum(1 for r in results if r['status'] == 'error')
        skipped_count = sum(1 for r in results if r['status'] == 'skipped')
        federated_results = federated_predict_house(results)

        return jsonify({
            'message': '评测完成',
            'summary': {
                'total': len(results),
                'success': success_count,
                'error': error_count,
                'skipped': skipped_count
            },
            'results': results,
            'federated_results': federated_results
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'评测失败: {str(e)}'}), 500

