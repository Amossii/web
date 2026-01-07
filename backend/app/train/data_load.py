import glob
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

def preprocess_df(raw_df, is_train=True):
    """
    raw_df: 原始 DataFrame
    is_train: True 表示训练集，会计算统计特征并 fit LabelEncoder；
              False 表示测试集，会复用传入的 stat_dict 和 label_encoders。
    stat_dict: 训练阶段计算好的统计特征字典：
        {
          "community": community_stat_df,
          "region":    region_stat_df,
          "street":    street_stat_df,
        }
    label_encoders: dict，保存每个类别列对应的 LabelEncoder（测试时复用）

    return:
        df_processed: 处理完且只保留关键列的 DataFrame
        stat_dict:    上述统计特征字典
        label_encoders: 类别特征编码器字典
    """
    if not is_train:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        enc_stats_path = os.path.join(current_dir, 'encoders_and_stats.pkl')

        saved = joblib.load(enc_stats_path)
        label_encoders = saved["label_encoders"]
        stat_dict = saved["stat_dict"]
        feature_cols = saved["feature_cols"]

    df = raw_df.copy()
    # ---------- 0. 删除套内面积 ----------
    if "套内面积" in df.columns:
        df = df.drop(columns=["套内面积"])

    # ---------- 1. 基本数值列 ----------
    if is_train:
        df["成交价格"] = pd.to_numeric(df["成交价格"], errors="coerce")  # 通常是万
        df["price_per_m2"] = pd.to_numeric(df["元/平"], errors="coerce")  # 标签

    def clean_area(x):
        if pd.isna(x):
            return np.nan
        x = str(x).replace("㎡", "").replace("平米", "").replace(" ", "")
        if x in ["暂无数据", ""]:
            return np.nan
        try:
            return float(x)
        except:
            return np.nan

    df["建筑面积"] = df["建筑面积"].apply(clean_area)

    for col in ["成交周期（天）", "调价（次）", "带看（次）", "关注（人）", "浏览（次）"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "建成年代" in df.columns:
        df["建成年代"] = pd.to_numeric(df["建成年代"], errors="coerce")

    # ---------- 2. 楼层解析 ----------
    def parse_floor_level(s):
        if pd.isna(s):
            return "未知"
        return str(s).split(" ")[0]  # "高楼层"

    def parse_total_floor(s):
        if pd.isna(s):
            return np.nan
        s = str(s)
        import re
        m = re.search(r"共(\d+)层", s)
        if m:
            return int(m.group(1))
        return np.nan

    df["楼层类别"] = df["所在楼层"].apply(parse_floor_level)
    df["总楼层"] = df["所在楼层"].apply(parse_total_floor)

    # ---------- 3. 时间 ----------
    df["成交时间_clean"] = df["成交时间"].astype(str).str.replace(" 成交", "", regex=False)
    df["成交时间_clean"] = pd.to_datetime(df["成交时间_clean"], errors="coerce", format="%Y.%m.%d")
    df["挂牌时间"] = pd.to_datetime(df["挂牌时间"], errors="coerce")

    df["成交_年份"] = df["成交时间_clean"].dt.year
    df["成交_月份"] = df["成交时间_clean"].dt.month
    df["在市天数"] = (df["成交时间_clean"] - df["挂牌时间"]).dt.days

    # ---------- 4. 经纬度 ----------
    def split_lng(x):
        if pd.isna(x):
            return np.nan
        try:
            return float(str(x).split(",")[0])
        except:
            return np.nan

    def split_lat(x):
        if pd.isna(x):
            return np.nan
        try:
            return float(str(x).split(",")[1])
        except:
            return np.nan

    df["lng"] = df["百度经纬"].apply(split_lng)
    df["lat"] = df["百度经纬"].apply(split_lat)

    # ---------- 5. 位置组合键，避免跨城重名 ----------
    # 确保这几列存在
    for col in ["城市", "区域", "街道", "小区"]:
        df[col] = df[col].astype(str)

    df["city_community"] = df["城市"] + "||" + df["小区"]
    df["city_region"] = df["城市"] + "||" + df["区域"]
    df["city_region_street"] = df["城市"] + "||" + df["区域"] + "||" + df["街道"]

    # ---------- 6. 统计特征（按 城市+小区 / 城市+区域 / 城市+区域+街道） ----------
    if is_train:
        comm_stat = (
            df.groupby("city_community")["price_per_m2"]
              .agg(["count", "mean"])
              .reset_index()
              .rename(columns={
                  "count": "community_cnt",
                  "mean": "community_mean_price"
              })
        )
        region_stat = (
            df.groupby("city_region")["price_per_m2"]
              .agg(["count", "mean"])
              .reset_index()
              .rename(columns={
                  "count": "region_cnt",
                  "mean": "region_mean_price"
              })
        )
        street_stat = (
            df.groupby("city_region_street")["price_per_m2"]
              .agg(["count", "mean"])
              .reset_index()
              .rename(columns={
                  "count": "street_cnt",
                  "mean": "street_mean_price"
              })
        )
        stat_dict = {
            "community": comm_stat,
            "region": region_stat,
            "street": street_stat,
        }
    else:
        comm_stat = stat_dict["community"]
        region_stat = stat_dict["region"]
        street_stat = stat_dict["street"]

    # merge 三层统计回去
    df = df.merge(comm_stat, on="city_community", how="left")
    df = df.merge(region_stat, on="city_region", how="left")
    df = df.merge(street_stat, on="city_region_street", how="left")
    if is_train:
        global_mean = df["price_per_m2"].mean()
        for mcol in ["community_mean_price", "region_mean_price", "street_mean_price"]:
            df[mcol] = df[mcol].fillna(global_mean)
        for ccol in ["community_cnt", "region_cnt", "street_cnt"]:
            df[ccol] = df[ccol].fillna(0)

    # ---------- 7. 类别特征编码 ----------
    cat_cols = [
        "城市",
        "区域",
        "街道",
        "小区",
        "房屋户型",
        "楼层类别",
        "建筑类型",
        "房屋朝向",
        "装修情况",
        "建筑结构",
        "供暖方式",
        "梯户比例",
        "配备电梯",
        "交易权属",
        "房屋用途",
        "房屋年限",
    ]

    if is_train:
        label_encoders = {}
        for col in cat_cols:
            if col not in df.columns:
                continue
            le = LabelEncoder()
            df[col] = df[col].astype(str).fillna("缺失")
            df[col + "_id"] = le.fit_transform(df[col])
            label_encoders[col] = le
    else:
        for col in cat_cols:
            if col not in df.columns:
                continue
            le = label_encoders[col]
            df[col] = df[col].astype(str).fillna("缺失")
            df[col] = df[col].map(lambda x: x if x in le.classes_ else le.classes_[0])
            df[col + "_id"] = le.transform(df[col])

    # ---------- 8. 数值缺失填充 ----------
    num_cols = [
        "成交价格",
        "建筑面积",
        "成交周期（天）",
        "调价（次）",
        "带看（次）",
        "关注（人）",
        "浏览（次）",
        "建成年代",
        "总楼层",
        "在市天数",
        "lng",
        "lat",
        "community_cnt",
        "community_mean_price",
        "region_cnt",
        "region_mean_price",
        "street_cnt",
        "street_mean_price",
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].astype(float)
            df[col] = df[col].fillna(df[col].median())

    # ---------- 9. 只保留关键特征 + 标签 ----------
    feature_cols = [
        # "成交价格",
        "建筑面积",
        "成交周期（天）",
        "调价（次）",
        "带看（次）",
        "关注（人）",
        "浏览（次）",
        "建成年代",
        "总楼层",
        "在市天数",
        "lng",
        "lat",
        "community_cnt",
        "community_mean_price",
        "region_cnt",
        "region_mean_price",
        "street_cnt",
        "street_mean_price",
        "成交_年份",
        "成交_月份",
    ]
    cat_id_cols = [c for c in df.columns if c.endswith("_id")]
    feature_cols = feature_cols + cat_id_cols
    keep_cols = feature_cols
    if is_train:
        keep_cols = feature_cols + ["price_per_m2"]  # 标签
    # keep_cols = feature_cols
    df_processed = df[keep_cols].copy()

    return df_processed

if __name__ == "__main__":
    df=pd.read_csv("./client0.csv")
    df_processed=preprocess_df(df,True)
    print(len(df_processed))
    print(df_processed.columns)
    print(df_processed.head())

