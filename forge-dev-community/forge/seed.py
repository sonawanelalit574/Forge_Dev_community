from forge import db
from forge.models import Comment, PollOption, Post, Space, User, Vote


def seed_if_empty() -> None:
    if User.query.first():
        return

    people = [
        ("demo", "Demo Member", "demo@forge.dev", "demo123", "Full-stack engineer", "Here to ask, share, and ship."),
        ("alex", "Alex Rivera", "alex@forge.dev", "forge123", "Staff platform engineer", "Distributed systems and Python internals."),
        ("priya", "Priya Shah", "priya@forge.dev", "forge123", "Product engineer", "Flask, design systems, and DX."),
        ("jordan", "Jordan Cole", "jordan@forge.dev", "forge123", "DevOps lead", "CI, containers, and calm on-call."),
    ]
    users = []
    for username, name, email, password, title, bio in people:
        user = User(username=username, display_name=name, email=email, title=title, bio=bio)
        user.set_password(password)
        db.session.add(user)
        users.append(user)

    spaces = [
        Space(slug="python", name="Python", blurb="Language, packaging, and internals.", accent="#7c8cff"),
        Space(slug="flask", name="Flask", blurb="Apps, blueprints, and production WSGI.", accent="#6ee7b7"),
        Space(slug="javascript", name="JavaScript", blurb="Front-end craft and Node.", accent="#fbbf24"),
        Space(slug="career", name="Career", blurb="Interviews, leveling, and teams.", accent="#fb7185"),
        Space(slug="devops", name="DevOps", blurb="Pipelines, cloud, and reliability.", accent="#38bdf8"),
        Space(slug="ai", name="AI", blurb="Models, evals, and shipping ML.", accent="#c084fc"),
        Space(slug="opensource", name="Open Source", blurb="Maintainers, licenses, PRs.", accent="#34d399"),
    ]
    db.session.add_all(spaces)
    db.session.flush()

    by_slug = {s.slug: s for s in spaces}
    demo, alex, priya, jordan = users

    posts = [
        Post(
            author=priya,
            kind="self",
            title="A calm Flask blueprint layout that still scales",
            body="Self-text: keep routes thin, models explicit, and seed data so empty rooms never happen.\n\n`create_app()` owns config. Blueprints own HTTP. Seed owns first impressions.\n\nIf you are starting a community product, ship a feed that already has voices in it.",
        ),
        Post(
            author=alex,
            kind="question",
            title="How do you keep SQLite migrations sane before Postgres?",
            body="We are still on SQLite for a private beta. When do you introduce Alembic without stalling the team?",
        ),
        Post(
            author=jordan,
            kind="link",
            title="Twelve-Factor still wins for small Flask shops",
            body="A reminder that config, logs, and process isolation beat clever frameworks.",
            url="https://12factor.net/",
        ),
        Post(
            author=demo,
            kind="poll",
            title="What should Forge ship next?",
            body="Vote so we build the loudest need first.",
        ),
        Post(
            author=jordan,
            kind="self",
            title="On-call notes from a quiet week",
            body="Self-text log: three alerts, one real incident, two noisy dashboards retired.\n\nIf a page never changes a decision, delete it.",
        ),
        Post(
            author=priya,
            kind="question",
            title="Best pattern for option buttons that actually switch composer panes?",
            body="We want Self-text / Question / Link / Poll to swap fields without a page reload. Vanilla JS is preferred.",
        ),
    ]
    posts[0].spaces = [by_slug["flask"], by_slug["python"]]
    posts[1].spaces = [by_slug["python"], by_slug["devops"]]
    posts[2].spaces = [by_slug["career"], by_slug["devops"]]
    posts[3].spaces = [by_slug["opensource"], by_slug["flask"]]
    posts[4].spaces = [by_slug["devops"]]
    posts[5].spaces = [by_slug["javascript"], by_slug["flask"]]

    db.session.add_all(posts)
    db.session.flush()

    poll = posts[3]
    db.session.add_all(
        [
            PollOption(post=poll, label="Private messages"),
            PollOption(post=poll, label="Code snippets with syntax color"),
            PollOption(post=poll, label="Job board"),
            PollOption(post=poll, label="Weekly digest"),
        ]
    )
    db.session.add_all(
        [
            Vote(post=posts[0], user_id=alex.id, value=1),
            Vote(post=posts[0], user_id=jordan.id, value=1),
            Vote(post=posts[1], user_id=priya.id, value=1),
            Vote(post=posts[2], user_id=demo.id, value=1),
            Vote(post=posts[5], user_id=alex.id, value=1),
            Comment(post=posts[0], author=alex, body="This is the right split. Seed data is product, not a chore."),
            Comment(post=posts[5], author=jordan, body="Use option buttons as a tablist, hide panes with a single `on` class, and keep kind in a hidden field."),
        ]
    )
    db.session.commit()
