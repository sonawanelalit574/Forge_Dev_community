import re
from datetime import datetime
from html import escape

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import desc, func, or_

from forge import db
from forge.models import Bookmark, Comment, PollOption, PollVote, Post, Space, User, Vote

auth_bp = Blueprint("auth", __name__)
main_bp = Blueprint("main", __name__)

KINDS = ("self", "question", "link", "poll")
KIND_LABELS = {
    "self": "Self-text",
    "question": "Question",
    "link": "Link",
    "poll": "Poll",
}


def _spaces():
    return Space.query.order_by(Space.name).all()


def _ago(dt: datetime) -> str:
    seconds = int((datetime.utcnow() - dt).total_seconds())
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 14:
        return f"{days}d ago"
    return dt.strftime("%b %d")


def _render_body(text: str) -> str:
    raw = escape(text or "")
    raw = re.sub(r"```([\s\S]*?)```", r"<pre><code>\1</code></pre>", raw)
    raw = re.sub(r"`([^`]+)`", r"<code>\1</code>", raw)
    raw = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", raw)
    raw = raw.replace("\n", "<br>")
    return raw


def _post_payload(post: Post, viewer=None) -> dict:
    viewer_id = viewer.id if viewer and getattr(viewer, "is_authenticated", False) else None
    vote = 0
    bookmarked = False
    poll_choice = None
    if viewer_id:
        v = Vote.query.filter_by(post_id=post.id, user_id=viewer_id).first()
        vote = v.value if v else 0
        bookmarked = Bookmark.query.filter_by(post_id=post.id, user_id=viewer_id).first() is not None
        if post.kind == "poll":
            chosen = (
                PollVote.query.join(PollOption)
                .filter(PollOption.post_id == post.id, PollVote.user_id == viewer_id)
                .first()
            )
            poll_choice = chosen.option_id if chosen else None

    poll_total = sum(opt.vote_count for opt in post.poll_options)
    return {
        "id": post.id,
        "kind": post.kind,
        "kind_label": KIND_LABELS.get(post.kind, post.kind),
        "title": post.title,
        "body": post.body,
        "body_html": _render_body(post.body),
        "url": post.url,
        "solved": post.solved,
        "score": post.score,
        "comments": post.comments.count(),
        "created": _ago(post.created_at),
        "author": {
            "id": post.author.id,
            "username": post.author.username,
            "name": post.author.display_name,
            "title": post.author.title,
        },
        "spaces": [{"slug": s.slug, "name": s.name, "accent": s.accent} for s in post.spaces],
        "viewer_vote": vote,
        "bookmarked": bookmarked,
        "poll": [
            {
                "id": opt.id,
                "label": opt.label,
                "votes": opt.vote_count,
                "pct": round((opt.vote_count / poll_total) * 100) if poll_total else 0,
            }
            for opt in post.poll_options
        ],
        "poll_total": poll_total,
        "poll_choice": poll_choice,
    }


@auth_bp.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.feed"))
    return render_template("auth.html", mode="login")


@auth_bp.post("/login")
def login_post():
    identity = (request.form.get("identity") or "").strip()
    password = request.form.get("password") or ""
    user = User.query.filter(or_(User.username == identity, User.email == identity)).first()
    if not user or not user.check_password(password):
        flash("Those credentials do not match a Forge member.", "error")
        return redirect(url_for("auth.login"))
    login_user(user)
    return redirect(url_for("main.feed"))


@auth_bp.get("/register")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.feed"))
    return render_template("auth.html", mode="register")


@auth_bp.post("/register")
def register_post():
    username = (request.form.get("username") or "").strip().lower()
    name = (request.form.get("display_name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    title = (request.form.get("title") or "Software engineer").strip()
    if not re.fullmatch(r"[a-z0-9_]{3,24}", username):
        flash("Username must be 3–24 letters, numbers, or underscores.", "error")
        return redirect(url_for("auth.register"))
    if len(password) < 6:
        flash("Password must be at least 6 characters.", "error")
        return redirect(url_for("auth.register"))
    if User.query.filter(or_(User.username == username, User.email == email)).first():
        flash("That username or email is already taken.", "error")
        return redirect(url_for("auth.register"))
    user = User(username=username, display_name=name or username, email=email, title=title)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return redirect(url_for("main.feed"))


@auth_bp.get("/logout")
def logout():
    logout_user()
    return redirect(url_for("main.landing"))


@main_bp.get("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("main.feed"))
    return render_template("landing.html", spaces=_spaces(), members=User.query.count(), posts=Post.query.count())


@main_bp.get("/feed")
@login_required
def feed():
    return render_template(
        "app.html",
        page="feed",
        spaces=_spaces(),
        kinds=KIND_LABELS,
        member=current_user,
    )


@main_bp.get("/compose")
@login_required
def compose():
    return render_template(
        "app.html",
        page="compose",
        spaces=_spaces(),
        kinds=KIND_LABELS,
        member=current_user,
    )


@main_bp.get("/posts/<int:post_id>")
@login_required
def post_page(post_id: int):
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)
    return render_template(
        "app.html",
        page="post",
        post_id=post_id,
        spaces=_spaces(),
        kinds=KIND_LABELS,
        member=current_user,
    )


@main_bp.get("/u/<username>")
@login_required
def profile(username: str):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template(
        "app.html",
        page="profile",
        profile_user=user,
        spaces=_spaces(),
        kinds=KIND_LABELS,
        member=current_user,
    )


@main_bp.get("/saved")
@login_required
def saved():
    return render_template(
        "app.html",
        page="saved",
        spaces=_spaces(),
        kinds=KIND_LABELS,
        member=current_user,
    )


@main_bp.get("/api/me")
@login_required
def api_me():
    return jsonify(
        {
            "id": current_user.id,
            "username": current_user.username,
            "name": current_user.display_name,
            "title": current_user.title,
        }
    )


@main_bp.get("/api/feed")
@login_required
def api_feed():
    kind = request.args.get("kind") or "all"
    space = request.args.get("space") or "all"
    sort = request.args.get("sort") or "latest"
    q = (request.args.get("q") or "").strip()
    saved_only = request.args.get("saved") == "1"
    author = request.args.get("author")

    query = Post.query
    if kind in KINDS:
        query = query.filter(Post.kind == kind)
    if space != "all":
        query = query.join(Post.spaces).filter(Space.slug == space)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Post.title.ilike(like), Post.body.ilike(like)))
    if saved_only:
        query = query.join(Bookmark).filter(Bookmark.user_id == current_user.id)
    if author:
        query = query.join(User, Post.author_id == User.id).filter(User.username == author)

    if sort == "top":
        query = (
            query.outerjoin(Vote)
            .group_by(Post.id)
            .order_by(desc(func.coalesce(func.sum(Vote.value), 0)), desc(Post.created_at))
        )
    elif sort == "unanswered":
        query = (
            query.filter(Post.kind == "question", Post.solved.is_(False))
            .outerjoin(Comment)
            .group_by(Post.id)
            .having(func.count(Comment.id) == 0)
            .order_by(desc(Post.created_at))
        )
    else:
        query = query.order_by(desc(Post.created_at))

    posts = query.limit(80).all()
    return jsonify([_post_payload(p, current_user) for p in posts])


@main_bp.get("/api/posts/<int:post_id>")
@login_required
def api_post(post_id: int):
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)
    comments = [
        {
            "id": c.id,
            "body": c.body,
            "body_html": _render_body(c.body),
            "created": _ago(c.created_at),
            "author": {"username": c.author.username, "name": c.author.display_name},
        }
        for c in post.comments.order_by(Comment.created_at)
    ]
    payload = _post_payload(post, current_user)
    payload["thread"] = comments
    return jsonify(payload)


@main_bp.post("/api/posts")
@login_required
def api_create_post():
    data = request.get_json(silent=True) or {}
    kind = data.get("kind") or "self"
    if kind not in KINDS:
        return jsonify({"error": "Unknown post type."}), 400
    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()
    url = (data.get("url") or "").strip()
    space_slugs = data.get("spaces") or []
    if len(title) < 8:
        return jsonify({"error": "Title needs at least 8 characters."}), 400
    if kind == "self" and len(body) < 12:
        return jsonify({"error": "Self-text needs a real body, not a stub."}), 400
    if kind == "question" and len(body) < 12:
        return jsonify({"error": "Questions need context in the body."}), 400
    if kind == "link" and not re.match(r"^https?://", url):
        return jsonify({"error": "Link posts need an http(s) URL."}), 400
    options = [str(o).strip() for o in (data.get("options") or []) if str(o).strip()]
    if kind == "poll" and len(options) < 2:
        return jsonify({"error": "Polls need at least two options."}), 400

    post = Post(author_id=current_user.id, kind=kind, title=title, body=body, url=url)
    db.session.add(post)
    db.session.flush()
    chosen = Space.query.filter(Space.slug.in_(space_slugs)).all() if space_slugs else []
    post.spaces = chosen[:4]
    if kind == "poll":
        for label in options[:6]:
            db.session.add(PollOption(post=post, label=label[:120]))
    db.session.commit()
    return jsonify(_post_payload(post, current_user)), 201


@main_bp.post("/api/posts/<int:post_id>/vote")
@login_required
def api_vote(post_id: int):
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)
    data = request.get_json(silent=True) or {}
    value = int(data.get("value") or 0)
    if value not in (-1, 1):
        return jsonify({"error": "Vote must be up or down."}), 400
    existing = Vote.query.filter_by(post_id=post.id, user_id=current_user.id).first()
    if existing and existing.value == value:
        db.session.delete(existing)
    elif existing:
        existing.value = value
    else:
        db.session.add(Vote(post_id=post.id, user_id=current_user.id, value=value))
    db.session.commit()
    db.session.refresh(post)
    return jsonify(_post_payload(post, current_user))


@main_bp.post("/api/posts/<int:post_id>/bookmark")
@login_required
def api_bookmark(post_id: int):
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)
    existing = Bookmark.query.filter_by(post_id=post.id, user_id=current_user.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"bookmarked": False})
    db.session.add(Bookmark(post_id=post.id, user_id=current_user.id))
    db.session.commit()
    return jsonify({"bookmarked": True})


@main_bp.post("/api/posts/<int:post_id>/comments")
@login_required
def api_comment(post_id: int):
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)
    data = request.get_json(silent=True) or {}
    body = (data.get("body") or "").strip()
    if len(body) < 2:
        return jsonify({"error": "Write a short reply first."}), 400
    comment = Comment(post=post, author=current_user, body=body)
    db.session.add(comment)
    db.session.commit()
    return jsonify({"ok": True})


@main_bp.post("/api/posts/<int:post_id>/solve")
@login_required
def api_solve(post_id: int):
    post = db.session.get(Post, post_id)
    if not post or post.author_id != current_user.id or post.kind != "question":
        abort(403)
    post.solved = not post.solved
    db.session.commit()
    return jsonify(_post_payload(post, current_user))


@main_bp.post("/api/poll/<int:option_id>")
@login_required
def api_poll_vote(option_id: int):
    option = db.session.get(PollOption, option_id)
    if not option:
        abort(404)
    existing = (
        PollVote.query.join(PollOption)
        .filter(PollOption.post_id == option.post_id, PollVote.user_id == current_user.id)
        .all()
    )
    for vote in existing:
        db.session.delete(vote)
    db.session.add(PollVote(option_id=option.id, user_id=current_user.id))
    db.session.commit()
    return jsonify(_post_payload(option.post, current_user))
