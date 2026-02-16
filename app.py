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
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///app.db")
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
    role = db.Column(db.String(10), nullable=False, default="user")  # "admin" or "user"
    status = db.Column(db.String(10), nullable=False, default="active")  # "active" or "inactive"

    def is_active(self) -> bool:
        # Flask-Login: inactive user cannot login
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
    status = db.Column(db.String(10), nullable=False, default="todo")  # todo/doing/done
    priority = db.Column(db.String(10), nullable=False, default="medium")  # low/medium/high

    assignee_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    is_deleted = db.Column(db.Boolean, nullable=False, default=False)

    assignee = db.relationship("User", foreign_keys=[assignee_user_id])
    creator = db.relationship("User", foreign_keys=[created_by_user_id])


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    try:
        uid = int(user_id)
    except ValueError:
        return None
    return db.session.get(User, uid)


# -------------------------
# Helpers
# -------------------------
def require_admin() -> None:
    if not current_user.is_authenticated:
        abort(401)
    if getattr(current_user, "role", "") != "admin":
        abort(403)


def parse_date(value: str) -> Optional[date]:
    # HTML date input: YYYY-MM-DD
    try:
        parts = value.split("-")
        if len(parts) != 3:
            return None
        y, m, d = map(int, parts)
        return date(y, m, d)
    except Exception:
        return None


def seed_if_empty() -> None:
    # users が空なら、研修用アカウントとタスクを投入
    if User.query.count() > 0:
        return

    admin = User(
        name="Admin",
        email="admin@example.com",
        password_hash=generate_password_hash("Admin1234"),
        role="admin",
        status="active",
    )
    u1 = User(
        name="Trainee A",
        email="user1@example.com",
        password_hash=generate_password_hash("User1234"),
        role="user",
        status="active",
    )
    u2 = User(
        name="Trainee B",
        email="user2@example.com",
        password_hash=generate_password_hash("User1234"),
        role="user",
        status="active",
    )
    inactive = User(
        name="Inactive User",
        email="inactive@example.com",
        password_hash=generate_password_hash("User1234"),
        role="user",
        status="inactive",
    )

    db.session.add_all([admin, u1, u2, inactive])
    db.session.commit()

    # タスクの種（正常/期限切れ/完了/他人担当）
    t1 = Task(
        title="Normal task",
        description="A normal task for user1",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 20),
        status="todo",
        priority="medium",
        assignee_user_id=u1.id,
        created_by_user_id=admin.id,
    )
    t2 = Task(
        title="Overdue task",
        description="End date in the past, not done",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 10),
        status="doing",
        priority="high",
        assignee_user_id=u1.id,
        created_by_user_id=admin.id,
    )
    t3 = Task(
        title="Done task",
        description="Done, even if end date is past",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 10),
        status="done",
        priority="low",
        assignee_user_id=u1.id,
        created_by_user_id=admin.id,
    )
    t4 = Task(
        title="Other user's task",
        description="Assigned to user2",
        start_date=date(2026, 4, 5),
        end_date=date(2026, 4, 25),
        status="todo",
        priority="medium",
        assignee_user_id=u2.id,
        created_by_user_id=admin.id,
    )

    db.session.add_all([t1, t2, t3, t4])
    db.session.commit()


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

        # 失敗理由を特定させない（固定メッセージ）
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

        if User.query.filter_by(email=email).first() is not None:
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
    # 管理者は全件（削除除外）、一般は自分担当のみ（削除除外）
    q = Task.query.filter_by(is_deleted=False)

    if current_user.role != "admin":
        q = q.filter_by(assignee_user_id=current_user.id)

    # 簡易検索・絞り込み（研修用の最低限）
    keyword = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip()

    if keyword:
        q = q.filter(Task.title.contains(keyword))
    if status in {"todo", "doing", "done"}:
        q = q.filter_by(status=status)

    tasks_list = q.order_by(Task.id.desc()).all()

    # 遅延表示は保存せず計算（フェーズ2の題材の一部を先に入れるならここ）
    today = date.today()
    def is_overdue(t: Task) -> bool:
        return (t.end_date < today) and (t.status != "done")

    return render_template("tasks.html", tasks=tasks_list, is_overdue=is_overdue, keyword=keyword, status=status)


def get_task_or_404(task_id: int) -> Task:
    t = db.session.get(Task, task_id)
    if t is None or t.is_deleted:
        abort(404)
    return t


def can_access_task(t: Task) -> bool:
    if current_user.role == "admin":
        return True
    return t.assignee_user_id == current_user.id


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
        if description is not None and len(description) > 2000:
            errors.append("説明は2000文字以内です。")

        sd = parse_date(start_date_raw)
        ed = parse_date(end_date_raw)
        if sd is None or ed is None:
            errors.append("開始日・終了日は日付形式で入力してください。")
        else:
            if sd > ed:
                errors.append("開始日は終了日以前の日付を指定してください。")

        if status not in {"todo", "doing", "done"}:
            errors.append("ステータスが不正です。")
        if priority not in {"low", "medium", "high"}:
            errors.append("優先度が不正です。")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("task_form.html", mode="new", task=None)

        # 一般ユーザーは担当者＝自分固定。管理者もまずは固定（割当はフェーズ2でSCR-11相当を追加）
        assignee_id = current_user.id

        t = Task(
            title=title,
            description=description,
            start_date=sd,
            end_date=ed,
            status=status,
            priority=priority,
            assignee_user_id=assignee_id,
            created_by_user_id=current_user.id,
            is_deleted=False,
        )
        db.session.add(t)
        db.session.commit()
        return redirect(url_for("task_detail", task_id=t.id))

    return render_template("task_form.html", mode="new", task=None)


@app.route("/tasks/<int:task_id>")
@login_required
def task_detail(task_id: int):
    t = get_task_or_404(task_id)
    if not can_access_task(t):
        # 研修用：権限外は403（404にする方針ならここを404に変える）
        abort(403)
    return render_template("task_form.html", mode="detail", task=t)


@app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def task_edit(task_id: int):
    t = get_task_or_404(task_id)
    if not can_access_task(t):
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
        if description is not None and len(description) > 2000:
            errors.append("説明は2000文字以内です。")

        sd = parse_date(start_date_raw)
        ed = parse_date(end_date_raw)
        if sd is None or ed is None:
            errors.append("開始日・終了日は日付形式で入力してください。")
        else:
            if sd > ed:
                errors.append("開始日は終了日以前の日付を指定してください。")

        if status not in {"todo", "doing", "done"}:
            errors.append("ステータスが不正です。")
        if priority not in {"low", "medium", "high"}:
            errors.append("優先度が不正です。")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("task_form.html", mode="edit", task=t)

        t.title = title
        t.description = description
        t.start_date = sd
        t.end_date = ed
        t.status = status
        t.priority = priority

        db.session.commit()
        return redirect(url_for("task_detail", task_id=t.id))

    return render_template("task_form.html", mode="edit", task=t)


@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def task_delete(task_id: int):
    t = get_task_or_404(task_id)
    if not can_access_task(t):
        abort(403)
    t.is_deleted = True
    db.session.commit()
    return redirect(url_for("tasks"))


# -------------------------
# Bootstrap DB
# -------------------------
def bootstrap() -> None:
    with app.app_context():
        db.create_all()
        seed_if_empty()


if __name__ == "__main__":
    bootstrap()
    app.run(host="0.0.0.0", port=8000, debug=True)
