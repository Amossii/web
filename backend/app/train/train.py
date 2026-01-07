import pandas as pd
import numpy as np
from lightgbm import LGBMRegressor, early_stopping, log_evaluation
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
import joblib

def load_data(train_df):
    target_col="price_per_m2"
    # 打印一下 NaN 情况，方便你自己看看
    print("=== 训练集 NaN 统计 ===")
    print(train_df.isna().sum()[train_df.isna().sum() > 0])

    # 1) 丢掉标签为 NaN 的样本（非常重要）
    before = len(train_df)
    train_df = train_df.dropna(subset=[target_col])
    after = len(train_df)
    print(f"\n训练集：丢弃了 {before - after} 行标签为 NaN 的样本，剩余 {after} 行")

    feature_cols = [c for c in train_df.columns if c != target_col]

    X_train_full = train_df[feature_cols].copy()
    y_train_full = train_df[target_col].astype(float)

    # 2) 对特征里的 NaN 做一次兜底填充（用列中位数）
    # （理论上我们在 preprocess 阶段就已经填过了，这里再保险一遍）
    X_train_full = X_train_full.fillna(X_train_full.median(numeric_only=True))
    return X_train_full, y_train_full


def train(X_train_full, y_train_full):
    # 再拆一块训练集出来做验证集
    X_train, X_valid, y_train, y_valid = train_test_split(
        X_train_full, y_train_full,
        test_size=0.1,
        random_state=42
    )
    print(X_train.columns)
    model = LGBMRegressor(
        learning_rate=0.05,
        num_leaves=64,
        n_estimators=5000,  # 大量的上限
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_valid, y_valid)],
        eval_metric='rmse',
        callbacks=[
            early_stopping(stopping_rounds=200),
            log_evaluation(50)
        ]
    )

    return model

def train_model(train_df):
    X_train_full, y_train_full = load_data(train_df)
    model = train(X_train_full, y_train_full)
    return model
if __name__ == '__main__':
    import lightgbm as lgb

    print(lgb.__version__)
