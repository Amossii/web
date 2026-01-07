from openpyxl.styles.builtins import total
from sklearn.preprocessing import StandardScaler
from app.train.data_load import preprocess_df
import pandas as pd
import os
NUM_COLS = [
    '建筑面积','成交周期（天）','调价（次）','带看（次）','关注（人）','浏览（次）',
    '建成年代','总楼层','在市天数','lng','lat',
    'community_cnt','community_mean_price',
    'region_cnt','region_mean_price',
    'street_cnt','street_mean_price'
]

CAT_COLS = [
    '城市_id','区域_id','街道_id','小区_id','房屋户型_id',
    '楼层类别_id','建筑类型_id','房屋朝向_id','装修情况_id',
    '建筑结构_id','供暖方式_id','梯户比例_id','配备电梯_id',
    '交易权属_id','房屋用途_id','房屋年限_id'
]

TARGET = 'price_per_m2'


def load_data(train_df):
    train_df = train_df.dropna(subset=[TARGET])

    # 数值特征
    X_num = train_df[NUM_COLS].fillna(train_df[NUM_COLS].median())
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, '1_scaler.pkl')
    scaler = joblib.load(path)

    X_num = scaler.fit_transform(X_num)

    # 类别特征
    X_cat = train_df[CAT_COLS].fillna(0).astype(int).values

    y = train_df[TARGET].values.astype('float32')

    return X_num, X_cat, y, scaler


import joblib
import torch
import torch.nn as nn

def get_cat_dims():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, 'cat_dims.pkl')
    cat_dims = joblib.load(path)
    return cat_dims

class HousePriceModel(nn.Module):
    def __init__(self, num_dim, cat_dims, embed_dim=16):
        super().__init__()

        # Embedding 层
        self.embeddings = nn.ModuleList([
            nn.Embedding(cat_dim + 1, embed_dim)
            for cat_dim in cat_dims
        ])

        emb_out_dim = embed_dim * len(cat_dims)

        self.mlp = nn.Sequential(
            nn.Linear(num_dim + emb_out_dim, 256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Dropout(0.2),

            nn.Linear(256, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(0.2),

            nn.Linear(128, 1)
        )

    def forward(self, x_num, x_cat):
        embs = [emb(x_cat[:, i]) for i, emb in enumerate(self.embeddings)]
        x = torch.cat([x_num] + embs, dim=1)
        return self.mlp(x).squeeze(1)


from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split


def train_dl(X_num, X_cat, y, cat_dims,epochs=2, batch_size=1024):
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    Xn_tr, Xn_va, Xc_tr, Xc_va, y_tr, y_va = train_test_split(
        X_num, X_cat, y, test_size=0.1, random_state=42
    )

    train_ds = TensorDataset(
        torch.tensor(Xn_tr, dtype=torch.float32),
        torch.tensor(Xc_tr, dtype=torch.long),
        torch.tensor(y_tr, dtype=torch.float32)
    )
    val_ds = TensorDataset(
        torch.tensor(Xn_va, dtype=torch.float32),
        torch.tensor(Xc_va, dtype=torch.long),
        torch.tensor(y_va, dtype=torch.float32)
    )

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size)

    model = HousePriceModel(
        num_dim=X_num.shape[1],
        cat_dims=cat_dims
    ).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    criterion = nn.MSELoss()

    best_rmse = 1e9
    patience, bad_epochs = 5, 0

    for epoch in range(epochs):
        model.train()
        for xn, xc, yb in train_loader:
            xn, xc, yb = xn.to(device), xc.to(device), yb.to(device)
            loss = criterion(model(xn, xc), yb)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        # 验证
        model.eval()
        preds, trues = [], []
        with torch.no_grad():
            for xn, xc, yb in val_loader:
                xn, xc = xn.to(device), xc.to(device)
                preds.append(model(xn, xc).cpu())
                trues.append(yb)

        preds = torch.cat(preds)
        trues = torch.cat(trues)
        rmse = torch.sqrt(((preds - trues) ** 2).mean()).item()

        print(f'Epoch {epoch + 1}, RMSE: {rmse:.2f}')

        if rmse < best_rmse:
            best_rmse = rmse
            bad_epochs = 0
            best_model = model.state_dict()
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                print('Early stopping')
                break

    model.load_state_dict(best_model)
    return model


def save_model(model, scaler, path='house_price_dl'):
    torch.save(model.state_dict(), f'{path}_model.pt')
    joblib.dump(scaler, f'{path}_scaler.pkl')
def get_scaler():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, '1_scaler.pkl')
    scaler = joblib.load(path)
    return scaler
def load_model(cat_dims, num_dim=17, path='1', device='cpu'):
    model = HousePriceModel(
        num_dim=num_dim,
        cat_dims=cat_dims
    )
    model.load_state_dict(torch.load(f'{path}_model.pt', map_location=device))
    model.to(device)
    model.eval()

    return  model
import numpy as np
import torch

def predict(df, model, scaler, device='cpu'):
    """
    df: DataFrame，结构和训练时一致（不包含 price_per_m2）
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, 'num_median.pkl')
    num_median = joblib.load(path)
    # 数值特征
    df = df.copy()
    for col in NUM_COLS:
        if col not in df.columns:
            df[col] = np.nan

    X_num = df[NUM_COLS].fillna(num_median)
    X_num = scaler.transform(X_num)

    X_cat = df[CAT_COLS].fillna(0).astype(int).values

    with torch.no_grad():
        xn = torch.tensor(X_num, dtype=torch.float32)
        xc = torch.tensor(X_cat, dtype=torch.long)
        pred = model(xn, xc)

    return pred.cpu().numpy()
def train_model(processed_df):
    cat_dims = get_cat_dims()
    a, b, c, d = load_data(processed_df)
    model = train_dl(a, b, c, cat_dims)
    return model
def eval_house_by_dict(house_info,model):
    cat_dims = get_cat_dims()
    df = pd.DataFrame([house_info])
    print(df)
    df_processed = preprocess_df(df)
    print(df_processed)
    scaler=get_scaler()
    unit = float(predict(df_processed, model, scaler)[0])
    total = float(unit*float(house_info['建筑面积'][:-1]))
    return unit,total
if __name__ == '__main__':

    cat_dims = get_cat_dims()
    # scaler=get_scaler()
    model = load_model(cat_dims)
    house_info={"小区": "民佳园小区","成交时间": "2021.01.01 成交","成交价格": 444,"元/平": 87986,"挂牌价格（万）": 446,"成交周期（天）": 67,"调价（次）": 0,"带看（次）": 6,"关注（人）": 13,"浏览（次）": 2133,"房屋户型": "1 室 1 厅 1 厨 1 卫","所在楼层": "高楼层 (共 7 层)","建筑面积": "50.44㎡","户型结构": "平层","套内面积": "暂无数据","建筑类型": "板楼","房屋朝向": "南 北","建成年代": 2000,"装修情况": "精装","建筑结构": "混合结构","供暖方式": "暂无数据","梯户比例": "一梯两户","配备电梯": "无","交易权属": "商品房","挂牌时间": "2020/10/27","房屋用途": "普通住宅","房屋年限": "暂无数据","房权所属": "非共有","百度经纬": "118.73926,32.07868","区域": "鼓楼","街道": "定淮门大街","城市": "南京"}
    a,b=eval_house_by_dict(house_info, model)
    print(a,b)
    # df = pd.DataFrame([house_info])
    #
    # df_processed = preprocess_df(df)
    # print(df_processed)
    # aa=predict(df_processed, model, scaler)
    # print(aa)