import joblib
import torch
import torch.nn as nn

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

def train_dl(X_num, X_cat, y, cat_dims, epochs=50, batch_size=1024):
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

        print(f'Epoch {epoch+1}, RMSE: {rmse:.2f}')

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

