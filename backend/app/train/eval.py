from app.train.data_load import preprocess_df
import pandas as pd
import joblib
def predict_house_price_by_df(house_features: pd.DataFrame, model):
    """
    输入一行标准特征结构（build_house_features 的输出）
    和训练好的模型，返回预测的单价和总价（如果有建筑面积）。

    参数
    ----
    house_features : pd.DataFrame
        一行特征，列顺序必须和训练时一致。
    model :
        训练好的 LightGBM / XGBoost 等回归模型，支持 .predict()。

    返回
    ----
    unit_price : float
        预测单价（元/平）
    total_price : float or None
        预测总价，如果能获取建筑面积；否则为 None。
    """
    # 1. 预测单价
    print("预测时的特征：")
    print(len(house_features.columns),house_features.columns)
    print("模型特征数：")
    print(model.n_features_in_)
    y_pred = model.predict(house_features)
    unit_price = float(y_pred[0])

    # 2. 如果有建筑面积，就顺便算一个总价
    total_price = None
    if "建筑面积" in house_features.columns:
        area = house_features["建筑面积"].iloc[0]
        if pd.notna(area):
            total_price = unit_price * float(area)

    return unit_price, total_price

def eval_house_by_dict(house_info,model):
    df = pd.DataFrame([house_info])


    df_processed = preprocess_df(df, is_train=False)
    unit_price, total_price = predict_house_price_by_df(df_processed, model)
    return unit_price, total_price
def federated_predict_house(results):
    """
    对多个客户端的预测结果进行加权平均融合

    参数:
        results (list): 包含多个客户端预测结果的列表，每个元素是一个字典，
                       需包含 "prediction" 键，其值为包含 "data_count",
                       "total_price", "unit_price" 的字典

    返回:
        dict: 包含加权平均后的总房价和单价，以及参与计算的客户端信息
    """
    # 初始化变量
    total_weight = 0  # 总权重（所有客户端data_count之和）
    weighted_total_price = 0  # 加权后的总房价之和
    weighted_unit_price = 0  # 加权后的单价之和
    valid_clients = []  # 记录有效参与的客户端信息

    # 遍历每个客户端的结果
    for result in results:
        # 检查结果是否成功且包含必要的预测信息
        if result.get("status") == "success" and result.get("prediction"):
            prediction = result["prediction"]
            # 提取必要的字段
            data_count = prediction.get("data_count", 0)
            total_price = prediction.get("total_price", 0)
            unit_price = prediction.get("unit_price", 0)
            client_id = result.get("client_id")
            client_name = result.get("client_name", f"Client {client_id}")

            # 只有当数据量大于0时才参与计算
            if data_count > 0:
                # 累加权重和加权后的预测值
                total_weight += data_count
                weighted_total_price += total_price * data_count
                weighted_unit_price += unit_price * data_count

                # 记录有效客户端信息
                valid_clients.append({
                    "client_id": client_id,
                    "client_name": client_name,
                    "data_count": data_count,
                    "weight_ratio": data_count / total_weight  # 权重占比（实时计算）
                })

    # 检查是否有有效数据
    if total_weight == 0:
        return {
            "error": "No valid prediction results found",
            "status": "failed",
            "result": None
        }

    # 计算加权平均值
    final_total_price = weighted_total_price / total_weight
    final_unit_price = weighted_unit_price / total_weight

    # 返回结果
    return {
            "weighted_average_total_price": final_total_price,
            "weighted_average_unit_price": final_unit_price,
            "total_data_count": total_weight,
            "participating_clients": valid_clients
    }

if __name__ == '__main__':
    dic={"小区": "民佳园小区","成交时间": "2021.01.01 成交","元/平": 87986,"挂牌价格（万）": 446,"成交周期（天）": 67,"调价（次）": 0,"带看（次）": 6,"关注（人）": 13,"浏览（次）": 2133,"房屋户型": "1 室 1 厅 1 厨 1 卫","所在楼层": "高楼层 (共 7 层)","建筑面积": "50.44㎡","户型结构": "平层","套内面积": "暂无数据","建筑类型": "板楼","房屋朝向": "南 北","建成年代": 2000,"装修情况": "精装","建筑结构": "混合结构","供暖方式": "暂无数据","梯户比例": "一梯两户","配备电梯": "无","交易权属": "商品房","挂牌时间": "2020/10/27","房屋用途": "普通住宅","房屋年限": "暂无数据","房权所属": "非共有","百度经纬": "118.73926,32.07868","区域": "鼓楼","街道": "定淮门大街","城市": "南京"}
    print("len(dic)=",len(dic))
    model = joblib.load("client0_trained_model.pkl")
    a,b=eval_house_by_dict(dic,model)
    print(a,b)