def build_house_features(house_info: dict) -> pd.DataFrame:
    enc_stats_path = "../../../encoders_and_stats.pkl"
    """
    根据一套房子的原始信息 + encoders_and_stats.pkl，
    生成【一行】和训练时完全一致的特征 DataFrame。

    参数
    ----
    house_info : dict
        一套房子的原始信息，比如：
        {
            "城市": "大连",
            "区域": "高新园区",
            "街道": "凌水",
            "小区": "大有恬园公寓",
            "建筑面积": 35.72,
            "建筑类型": "塔楼",
            "房屋朝向": "南",
            "装修情况": "精装",
            "建筑结构": "钢混结构",
            "供暖方式": "集中供暖",
            "梯户比例": "四梯三十四户",
            "配备电梯": "有",
            "所在楼层": "高楼层 (共4层)",
            "成交时间": "2021.01.01 成交",    # 可选，没有就当缺失
            "挂牌时间": "2020-04-20",          # 可选
            "百度经纬": "121.518155,38.884228"  # 可选
            ...
        }
        缺的字段会自动按“缺失”处理。

    enc_stats_path : str
        训练阶段保存的 encoders_and_stats.pkl 路径。

    返回
    ----
    features_df : pd.DataFrame
        只有一行，列顺序和训练时 feature_cols 完全一致。
    """
    saved = joblib.load(enc_stats_path)
    label_encoders = saved["label_encoders"]
    stat_dict = saved["stat_dict"]
    feature_cols = saved["feature_cols"]

    # ---------- 0. 构造单行原始 DataFrame ----------
    df = pd.DataFrame([house_info])

    # 确保这些关键原始列至少存在（即使是 NaN）
    base_cols = [
        "城市", "区域", "街道", "小区",
        "建筑面积",
        "成交价格", "成交周期（天）", "调价（次）",
        "带看（次）", "关注（人）", "浏览（次）",
        "建成年代",
        "房屋户型", "建筑类型", "房屋朝向", "装修情况",
        "建筑结构", "供暖方式", "梯户比例", "配备电梯",
        "交易权属", "房屋用途", "房屋年限",
        "所在楼层",
        "成交时间", "挂牌时间",
        "百度经纬",
    ]
    for col in base_cols:
        if col not in df.columns:
            df[col] = np.nan

    # ---------- 1. 数值列清洗 ----------
    # 建筑面积：去掉"㎡"等
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

    # 其他可选数值列
    num_cols_raw = ["成交价格", "成交周期（天）", "调价（次）", "带看（次）", "关注（人）", "浏览（次）", "建成年代"]
    for col in num_cols_raw:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # ---------- 2. 楼层解析 ----------
    def parse_floor_level(s):
        if pd.isna(s):
            return "未知"
        return str(s).split(" ")[0]  # "高楼层"

    def parse_total_floor(s):
        if pd.isna(s):
            return np.nan
        s = str(s)
        m = re.search(r"共(\d+)层", s)
        if m:
            return int(m.group(1))
        return np.nan

    df["楼层类别"] = df["所在楼层"].apply(parse_floor_level)
    df["总楼层"] = df["所在楼层"].apply(parse_total_floor)

    # ---------- 3. 时间解析 ----------
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

    # ---------- 5. 位置组合键（防止跨城重名） ----------
    for col in ["城市", "区域", "街道", "小区"]:
        df[col] = df[col].astype(str)

    df["city_community"] = df["城市"] + "||" + df["小区"]
    df["city_region"] = df["城市"] + "||" + df["区域"]
    df["city_region_street"] = df["城市"] + "||" + df["区域"] + "||" + df["街道"]

    # ---------- 6. 小区 / 区域 / 街道统计特征 ----------
    comm_stat = stat_dict["community"]   # 训练阶段算好的
    region_stat = stat_dict["region"]
    street_stat = stat_dict["street"]

    # 全局均价（用于没匹配上的小区/区域/街道）
    # 用样本数加权平均更合理
    comm_cnt = comm_stat["community_cnt"]
    comm_mean = comm_stat["community_mean_price"]
    if comm_cnt.sum() > 0:
        global_mean = (comm_mean * comm_cnt).sum() / comm_cnt.sum()
    else:
        global_mean = comm_mean.mean()

    # merge 三层统计
    df = df.merge(comm_stat, on="city_community", how="left")
    df = df.merge(region_stat, on="city_region", how="left")
    df = df.merge(street_stat, on="city_region_street", how="left")

    # 填充统计特征缺失
    for mcol in ["community_mean_price", "region_mean_price", "street_mean_price"]:
        if mcol in df.columns:
            df[mcol] = df[mcol].fillna(global_mean)
    for ccol in ["community_cnt", "region_cnt", "street_cnt"]:
        if ccol in df.columns:
            df[ccol] = df[ccol].fillna(0)

    # ---------- 7. 类别特征编码（用训练时的 LabelEncoder） ----------
    # label_encoders 的 key 就是我们当时 encode 的那些列名
    for col, le in label_encoders.items():
        # 如果本来就没有这一列，先填成"缺失"
        if col not in df.columns:
            df[col] = "缺失"
        else:
            df[col] = df[col].astype(str).fillna("缺失")

        # 新数据中可能出现训练时没见过的类别：映射到"缺失"或第一个类别
        # 确保 "缺失" 在 classes_ 里
        classes = list(le.classes_)
        default_cls = "缺失" if "缺失" in classes else classes[0]

        val = df.at[0, col]
        if val not in classes:
            val = default_cls
        df.at[0, col] = val

        df[col + "_id"] = le.transform([val])[0]

    # ---------- 8. 组装成模型需要的特征结构 ----------
    # 有些列在这一套房子里可能压根没用到（比如某些统计列），这里保证都存在
    for col in feature_cols:
        if col not in df.columns:
            # 数值型就填 NaN，LightGBM 预测时可以自动处理 NaN
            df[col] = np.nan

    # 按训练时的列顺序取出
    features_df = df[feature_cols].copy()

    return features_df