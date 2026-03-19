# Training Task App Architecture

## 概要

このアプリケーションは、社内QA研修で使用するための簡易タスク管理Webアプリです。

目的

・テスト設計の題材として利用する  
・要件定義書 / 設計書の読み方を学ぶ  
・テストケース作成の演習に利用する  

実運用は想定していません。

---

# システム構成

ユーザー
↓
ブラウザ
↓
Flaskアプリケーション
↓
SQLAlchemy
↓
Database

開発環境

・Backend : Flask
・ORM : SQLAlchemy
・Auth : Flask-Login
・DB : SQLite（ローカル） / Postgres（公開環境）
・Server : Gunicorn
・Hosting : Render

---

# ディレクトリ構成
training-task-app
│
├ app.py
├ requirements.txt
├ templates
│ ├ login.html
│ ├ register.html
│ ├ tasks.html
│ ├ task_form.html
│ └ base.html
│
└ docs


---

# データモデル

## User

|項目|型|説明|
|---|---|---|
|id|int|ユーザーID|
|name|string|ユーザー名|
|email|string|メールアドレス|
|password_hash|string|ハッシュ化パスワード|
|role|string|admin / user|
|status|string|active / inactive|

---

## Task

|項目|型|説明|
|---|---|---|
|id|int|タスクID|
|title|string|タイトル|
|description|string|説明|
|start_date|date|開始日|
|end_date|date|終了日|
|status|string|todo / doing / done|
|priority|string|low / medium / high|
|assignee_user_id|int|担当ユーザー|
|created_by_user_id|int|作成者|
|is_deleted|bool|論理削除|

---

# 権限設計

|Role|権限|
|---|---|
|admin|全タスク閲覧可能|
|user|自分のタスクのみ閲覧可能|

---

# 遅延判定

以下条件で遅延と判定
end_date < today AND status != done


---

# セキュリティ設計

実装済み

・パスワードハッシュ化  
・ログイン認証  
・権限チェック  
・論理削除  

未実装（研修用）

・CSRF  
・レート制限  
・監査ログ  

---

# 初期データ

初回起動時に以下を自動生成

ユーザー

admin@example.com  
user1@example.com  
user2@example.com  

タスク

・通常タスク  
・期限切れタスク  
・他ユーザータスク

---

# 想定ユーザー

社内QA研修受講者

利用目的

・テスト観点抽出  
・テストケース作成  
・仕様理解演習