from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from forge import db

post_tags = db.Table(
    "post_tags",
    db.Column("post_id", db.Integer, db.ForeignKey("posts.id"), primary_key=True),
    db.Column("space_id", db.Integer, db.ForeignKey("spaces.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    display_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    title = db.Column(db.String(120), default="Software engineer")
    bio = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    posts = db.relationship("Post", backref="author", lazy="dynamic")
    comments = db.relationship("Comment", backref="author", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Space(db.Model):
    __tablename__ = "spaces"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(60), nullable=False)
    blurb = db.Column(db.String(160), default="")
    accent = db.Column(db.String(20), default="#7c8cff")


class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    kind = db.Column(db.String(20), nullable=False, default="self")  # self, question, link, poll
    title = db.Column(db.String(180), nullable=False)
    body = db.Column(db.Text, default="")
    url = db.Column(db.String(400), default="")
    solved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    spaces = db.relationship("Space", secondary=post_tags, backref="posts")
    comments = db.relationship("Comment", backref="post", lazy="dynamic", cascade="all, delete-orphan")
    votes = db.relationship("Vote", backref="post", lazy="dynamic", cascade="all, delete-orphan")
    bookmarks = db.relationship("Bookmark", backref="post", lazy="dynamic", cascade="all, delete-orphan")
    poll_options = db.relationship("PollOption", backref="post", cascade="all, delete-orphan", order_by="PollOption.id")

    @property
    def score(self) -> int:
        return sum(v.value for v in self.votes)


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Vote(db.Model):
    __tablename__ = "votes"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    value = db.Column(db.Integer, nullable=False)  # 1 or -1
    __table_args__ = (db.UniqueConstraint("post_id", "user_id"),)


class Bookmark(db.Model):
    __tablename__ = "bookmarks"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    __table_args__ = (db.UniqueConstraint("post_id", "user_id"),)


class PollOption(db.Model):
    __tablename__ = "poll_options"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    label = db.Column(db.String(120), nullable=False)
    votes = db.relationship("PollVote", backref="option", cascade="all, delete-orphan")

    @property
    def vote_count(self) -> int:
        return len(self.votes)


class PollVote(db.Model):
    __tablename__ = "poll_votes"
    id = db.Column(db.Integer, primary_key=True)
    option_id = db.Column(db.Integer, db.ForeignKey("poll_options.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    __table_args__ = (db.UniqueConstraint("option_id", "user_id"),)
