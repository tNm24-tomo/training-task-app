from __future__ import annotations

import os
from datetime import date
from typing import Optional

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

app = Flask(__name__)

# 環境変数
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

app.config["SECRET_KEY"] = SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


# -------------------------
# Models
# -------------------------
class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(254), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="user")  # admin / user
    status = db.Column(db.String(10), nullable=False, default="active")  # active / inactive

    def is_active(self) -> bool:
        return self.status == "active"

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(2000), nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), nullable=False, default="todo")  # todo / doing / done
    priority = db.Column(db.String(10), nullable=False, default="medium")  # low / medium / high

    assignee_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    is_deleted = db.Column(db.Boolean, nullable=False, default=False)

    assignee = db.relationship("User", foreign_keys=[assignee_user_id])
    creator = db.relationship("User", foreign_keys=[created_by_user_id])


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return None


# -------------------------
# Helpers
# -------------------------
def parse_date(value: str) -> Optional[date]:
    try:
        y, m, d = map(int, value.split("-"))
        return date(y, m, d)
    except Exception:
        return None


def get_task_or_404(task_id: int) -> Task:
    task = db.session.get(Task, task_id)
    if task is None or task.is_deleted:
        abort(404)
    return task


def can_access_task(task: Task) -> bool:
    if current_user.role == "admin":
        return True
    return task.assignee_user_id == current_user.id


def seed_if_empty() -> None:
    """
    初回だけダミーユーザーとダミータスクを作る
    """
    if User.query.count() > 0:
        return

    admin = User(
        name="Admin",
        email="admin@example.com",
        password_hash=generate_password_hash("Admin1234"),
        role="admin",
        status="active",
    )
    user1 = User(
        name="Trainee A",
        email="user1@example.com",
        password_hash=generate_password_hash("User1234"),
        role="user",
        status="active",
    )
    user2 = User(
        name="Trainee B",
        email="user2@example.com",
        password_hash=generate_password_hash("User1234"),
        role="user",
        status="active",
    )

    db.session.add_all([admin, user1, user2])
    db.session.commit()

    tasks = [
        Task(
            title="Normal task",
            description="A normal task for user1",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 20),
            status="todo",
            priority="medium",
            assignee_user_id=user1.id,
            created_by_user_id=admin.id,
        ),
        Task(
            title="Overdue task",
            description="Past end date and not completed",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
            status="doing",
            priority="high",
            assignee_user_id=user1.id,
            created_by_user_id=admin.id,
        ),
        Task(
            title="Other user's task",
            description="Assigned to user2",
            start_date=date(2026, 4, 5),
            end_date=date(2026, 4, 25),
            status="todo",
            priority="medium",
            assignee_user_id=user2.id,
            created_by_user_id=admin.id,
        ),
    ]
    db.session.add_all(tasks)
    db.session.commit()


def bootstrap() -> None:
    with app.app_context():
        db.create_all()
        seed_if_empty()


# -------------------------
# Routes
# -------------------------
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("tasks"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        user = User.query.filter_by(email=email).first()

        if (user is None) or (not user.check_password(password)) or (user.status != "active"):
            flash("メールアドレスまたはパスワードが違います。", "error")
            return render_template("login.html")

        login_user(user)
        return redirect(url_for("tasks"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""

        errors = []

        if not name:
            errors.append("氏名は必須です。")
        if len(name) > 50:
            errors.append("氏名は50文字以内です。")

        if not email:
            errors.append("メールは必須です。")
        if len(email) > 254:
            errors.append("メールは254文字以内です。")
        if "@" not in email:
            errors.append("メール形式が不正です。")

        if not password:
            errors.append("パスワードは必須です。")
        if len(password) < 8 or len(password) > 72:
            errors.append("パスワードは8〜72文字です。")
        if password.strip() == "":
            errors.append("パスワードが空白のみは不可です。")
        if password != password2:
            errors.append("パスワード確認が一致しません。")

        if User.query.filter_by(email=email).first():
            errors.append("このメールは既に登録されています。")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html")

        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            role="user",
            status="active",
        )
        db.session.add(user)
        db.session.commit()

        flash("登録が完了しました。ログインしてください。", "info")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/tasks")
@login_required
def tasks():
    query = Task.query.filter_by(is_deleted=False)

    if current_user.role != "admin":
        query = query.filter_by(assignee_user_id=current_user.id)

    keyword = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip()

    if keyword:
        query = query.filter(Task.title.contains(keyword))
    if status in {"todo", "doing", "done"}:
        query = query.filter_by(status=status)

    task_list = query.order_by(Task.id.desc()).all()

    today = date.today()

    def is_overdue(task: Task) -> bool:
        return (task.end_date < today) and (task.status != "done")

    return render_template(
        "tasks.html",
        tasks=task_list,
        keyword=keyword,
        status=status,
        is_overdue=is_overdue,
    )


@app.route("/tasks/new", methods=["GET", "POST"])
@login_required
def task_new():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip() or None
        start_date_raw = request.form.get("start_date") or ""
        end_date_raw = request.form.get("end_date") or ""
        status = (request.form.get("status") or "todo").strip()
        priority = (request.form.get("priority") or "medium").strip()

        errors = []

        if not title:
            errors.append("タイトルは必須です。")
        if len(title) > 100:
            errors.append("タイトルは100文字以内です。")
        if description and len(description) > 2000:
            errors.append("説明は2000文字以内です。")

        start_date = parse_date(start_date_raw)
        end_date = parse_date(end_date_raw)

        if start_date is None or end_date is None:
            errors.append("開始日・終了日は日付形式で入力してください。")
        elif start_date > end_date:
            errors.append("開始日は終了日以前の日付を指定してください。")

        if status not in {"todo", "doing", "done"}:
            errors.append("ステータスが不正です。")
        if priority not in {"low", "medium", "high"}:
            errors.append("優先度が不正です。")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("task_form.html", mode="new", task=None)

        task = Task(
            title=title,
            description=description,
            start_date=start_date,
            end_date=end_date,
            status=status,
            priority=priority,
            assignee_user_id=current_user.id,
            created_by_user_id=current_user.id,
            is_deleted=False,
        )
        db.session.add(task)
        db.session.commit()

        return redirect(url_for("task_detail", task_id=task.id))

    return render_template("task_form.html", mode="new", task=None)


@app.route("/tasks/<int:task_id>")
@login_required
def task_detail(task_id: int):
    task = get_task_or_404(task_id)
    if not can_access_task(task):
        abort(403)
    return render_template("task_form.html", mode="detail", task=task)


@app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def task_edit(task_id: int):
    task = get_task_or_404(task_id)
    if not can_access_task(task):
        abort(403)

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip() or None
        start_date_raw = request.form.get("start_date") or ""
        end_date_raw = request.form.get("end_date") or ""
        status = (request.form.get("status") or "todo").strip()
        priority = (request.form.get("priority") or "medium").strip()

        errors = []

        if not title:
            errors.append("タイトルは必須です。")
        if len(title) > 100:
            errors.append("タイトルは100文字以内です。")
        if description and len(description) > 2000:
            errors.append("説明は2000文字以内です。")

        start_date = parse_date(start_date_raw)
        end_date = parse_date(end_date_raw)

        if start_date is None or end_date is None:
            errors.append("開始日・終了日は日付形式で入力してください。")
        elif start_date > end_date:
            errors.append("開始日は終了日以前の日付を指定してください。")

        if status not in {"todo", "doing", "done"}:
            errors.append("ステータスが不正です。")
        if priority not in {"low", "medium", "high"}:
            errors.append("優先度が不正です。")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("task_form.html", mode="edit", task=task)

        task.title = title
        task.description = description
        task.start_date = start_date
        task.end_date = end_date
        task.status = status
        task.priority = priority
        db.session.commit()

        return redirect(url_for("task_detail", task_id=task.id))

    return render_template("task_form.html", mode="edit", task=task)


@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def task_delete(task_id: int):
    task = get_task_or_404(task_id)
    if not can_access_task(task):
        abort(403)

    task.is_deleted = True
    db.session.commit()
    return redirect(url_for("tasks"))


# 起動時にテーブル作成と初期データ投入
bootstrap()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)