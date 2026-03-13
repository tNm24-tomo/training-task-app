# training-task-app

研修用のタスク管理Webアプリです。  
実運用は想定していません。

## 主な機能
- ログイン / ログアウト
- ユーザー登録
- タスク作成 / 一覧 / 編集 / 論理削除
- 管理者 / 一般ユーザーの権限分離
- 遅延表示

## ローカル起動
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac
source venv/bin/activate

pip install -r requirements.txt
python app.py
