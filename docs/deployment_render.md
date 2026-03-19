# Deployment Guide (Render)

このアプリは Render を利用して公開することができます。

目的

・社内メンバーがブラウザからアクセスできるようにする  
・QA研修で実際に操作してもらう

---

# 必要なもの

・GitHubアカウント  
・Renderアカウント  

---

# デプロイ構成

Browser  
↓  
Render Web Service  
↓  
Postgres Database

---

# 手順

## 1 GitHubにpush
git add .
git commit -m "prepare deployment"
git push origin main


---

## 2 RenderでPostgres作成

Dashboard

New  
↓  
PostgreSQL

---

## 3 Web Service作成

Render Dashboard

New  
↓  
Web Service  
↓  
GitHub repository選択

---

## 設定

Build Command
pip install -r requirements.txt

Start Command
gunicorn app:app


---

# 環境変数

Render の Environment Variables に設定

SECRET_KEY
ランダム文字列


DATABASE_URL
Render Postgres の接続URL


---

# デプロイ

Deploy ボタンを押す

成功すると
https://xxxxx.onrender.com

のURLが発行される

---

# 社内共有

URLを社内メンバーに共有

ログインアカウント

管理者

admin@example.com  

一般

user1@example.com  

---

# 注意

本アプリは研修用です

本番利用は想定していません

実運用には以下が必要です

・CSRF対策  
・監査ログ  
・セッション管理強化  
・アクセス制御