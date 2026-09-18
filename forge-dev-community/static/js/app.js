const stage = document.querySelector(".stage");
if (!stage) {
  // landing only
} else {
  boot();
}

function boot() {
  const page = stage.dataset.page;
  bindSpaceButtons();
  if (page === "compose") bindComposer();
  if (page === "post") loadThread(stage.dataset.postId);
  if (page === "feed" || page === "saved" || page === "profile") bindFeed();
}

const state = {
  kind: "all",
  sort: "latest",
  space: "all",
  q: "",
};

function bindSpaceButtons() {
  document.querySelectorAll(".space-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const slug = btn.dataset.space;
      state.space = state.space === slug ? "all" : slug;
      document.querySelectorAll(".space-btn").forEach((b) => b.classList.toggle("on", b.dataset.space === state.space));
      if (stage.dataset.page === "compose") {
        document.querySelectorAll('input[name="spaces"]').forEach((el) => {
          el.checked = state.space !== "all" && el.value === state.space;
        });
        return;
      }
      if (stage.dataset.page === "post") {
        window.location.href = `/feed`;
        return;
      }
      loadFeed();
    });
  });
}

function bindComposer() {
  const kindField = document.getElementById("kind-field");
  const buttons = document.querySelectorAll(".composer .opt[data-kind]");
  const panes = document.querySelectorAll(".composer-pane");

  const setKind = (kind) => {
    kindField.value = kind;
    buttons.forEach((btn) => {
      const on = btn.dataset.kind === kind;
      btn.classList.toggle("on", on);
      btn.setAttribute("aria-selected", String(on));
    });
    panes.forEach((pane) => pane.classList.toggle("on", pane.dataset.pane === kind));
  };

  buttons.forEach((btn) => btn.addEventListener("click", () => setKind(btn.dataset.kind)));
  setKind("self");

  document.getElementById("add-option").addEventListener("click", () => {
    const box = document.getElementById("poll-options");
    if (box.children.length >= 6) return;
    const input = document.createElement("input");
    input.placeholder = `Option ${String.fromCharCode(65 + box.children.length)}`;
    box.appendChild(input);
  });

  document.getElementById("compose-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const kind = kindField.value;
    const payload = {
      kind,
      title: document.getElementById("title-field").value.trim(),
      spaces: [...document.querySelectorAll('input[name="spaces"]:checked')].map((el) => el.value),
      body: "",
      url: "",
      options: [],
    };
    if (kind === "self") payload.body = document.getElementById("self-body").value.trim();
    if (kind === "question") payload.body = document.getElementById("question-body").value.trim();
    if (kind === "link") {
      payload.url = document.getElementById("link-url").value.trim();
      payload.body = document.getElementById("link-body").value.trim();
    }
    if (kind === "poll") {
      payload.body = document.getElementById("poll-body").value.trim();
      payload.options = [...document.querySelectorAll("#poll-options input")].map((el) => el.value.trim()).filter(Boolean);
    }
    const errorEl = document.getElementById("compose-error");
    const res = await fetch("/api/posts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      errorEl.hidden = false;
      errorEl.textContent = data.error || "Could not publish.";
      return;
    }
    window.location.href = `/posts/${data.id}`;
  });
}

function bindFeed() {
  document.querySelectorAll('[data-filter="sort"] .opt').forEach((btn) => {
    btn.addEventListener("click", () => {
      state.sort = btn.dataset.sort;
      toggleGroup(btn);
      loadFeed();
    });
  });
  document.querySelectorAll('[data-filter="kind"] .opt').forEach((btn) => {
    btn.addEventListener("click", () => {
      state.kind = btn.dataset.kind;
      toggleGroup(btn);
      loadFeed();
    });
  });
  const search = document.getElementById("search");
  if (search) {
    let timer;
    search.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        state.q = search.value.trim();
        loadFeed();
      }, 220);
    });
  }
  loadFeed();
}

function toggleGroup(btn) {
  btn.parentElement.querySelectorAll(".opt").forEach((el) => el.classList.toggle("on", el === btn));
}

async function loadFeed() {
  const feed = document.getElementById("feed");
  if (!feed) return;
  const params = new URLSearchParams({
    kind: state.kind,
    sort: state.sort,
    space: state.space,
    q: state.q,
    saved: stage.dataset.saved || "0",
  });
  if (stage.dataset.author) params.set("author", stage.dataset.author);
  const res = await fetch(`/api/feed?${params}`);
  const posts = await res.json();
  if (!posts.length) {
    feed.innerHTML = `<p class="empty">No threads match those option buttons yet.</p>`;
    return;
  }
  feed.innerHTML = posts.map(postCard).join("");
  bindCardActions(feed);
}

async function loadThread(id) {
  const root = document.getElementById("thread-root");
  const res = await fetch(`/api/posts/${id}`);
  if (!res.ok) {
    root.innerHTML = `<p class="empty">Thread not found.</p>`;
    return;
  }
  const post = await res.json();
  root.innerHTML = `
    ${postCard(post, true)}
    <form class="reply-box">
      <label>Reply
        <textarea required minlength="2" rows="4" placeholder="Write a precise reply."></textarea>
      </label>
      <button class="solid" type="submit">Post reply</button>
    </form>
    <div class="thread">
      ${(post.thread || []).map((c) => `
        <article class="comment">
          <header>${escapeHtml(c.author.name)} · @${escapeHtml(c.author.username)} · ${escapeHtml(c.created)}</header>
          <div>${c.body_html}</div>
        </article>
      `).join("") || `<p class="empty">No replies yet.</p>`}
    </div>
  `;
  bindCardActions(root);
  root.querySelector(".reply-box").addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = root.querySelector("textarea").value.trim();
    await fetch(`/api/posts/${id}/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body }),
    });
    loadThread(id);
  });
}

function postCard(post, expanded = false) {
  const poll = (post.poll || [])
    .map(
      (opt) => `
      <button type="button" class="poll-opt ${post.poll_choice === opt.id ? "on" : ""}" data-poll="${opt.id}" style="--pct:${opt.pct}%">
        <span class="bar"></span>
        <b>${escapeHtml(opt.label)}</b>
        <span>${opt.votes} · ${opt.pct}%</span>
      </button>`
    )
    .join("");
  return `
    <article class="card" data-id="${post.id}">
      <div class="votes">
        <button type="button" class="${post.viewer_vote === 1 ? "on" : ""}" data-vote="1" aria-label="Upvote">▲</button>
        <b>${post.score}</b>
        <button type="button" class="${post.viewer_vote === -1 ? "on" : ""}" data-vote="-1" aria-label="Downvote">▼</button>
      </div>
      <div>
        <div class="kind-tag">${escapeHtml(post.kind_label)}${post.solved ? " · solved" : ""}</div>
        <h2><a href="/posts/${post.id}">${escapeHtml(post.title)}</a></h2>
        ${post.url ? `<p class="excerpt"><a href="${escapeAttr(post.url)}" target="_blank" rel="noopener">${escapeHtml(post.url)}</a></p>` : ""}
        <div class="excerpt">${expanded ? post.body_html : escapeHtml((post.body || "").slice(0, 220))}</div>
        ${post.kind === "poll" ? `<div class="poll-list">${poll}</div>` : ""}
        <div class="meta">
          <a href="/u/${escapeAttr(post.author.username)}">${escapeHtml(post.author.name)}</a>
          <span>${escapeHtml(post.created)}</span>
          ${post.spaces.map((s) => `<span class="pill">${escapeHtml(s.name)}</span>`).join("")}
          <span>${post.comments} replies</span>
          <button type="button" class="icon-btn ${post.bookmarked ? "on" : ""}" data-save>Save</button>
          ${post.kind === "question" ? `<button type="button" class="icon-btn ${post.solved ? "on" : ""}" data-solve>Solved</button>` : ""}
        </div>
      </div>
    </article>
  `;
}

function bindCardActions(root) {
  root.querySelectorAll(".card").forEach((card) => {
    const id = card.dataset.id;
    card.querySelectorAll("[data-vote]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await fetch(`/api/posts/${id}/vote`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ value: Number(btn.dataset.vote) }),
        });
        refreshCurrent(id);
      });
    });
    const save = card.querySelector("[data-save]");
    if (save) {
      save.addEventListener("click", async () => {
        await fetch(`/api/posts/${id}/bookmark`, { method: "POST" });
        refreshCurrent(id);
      });
    }
    const solve = card.querySelector("[data-solve]");
    if (solve) {
      solve.addEventListener("click", async () => {
        await fetch(`/api/posts/${id}/solve`, { method: "POST" });
        refreshCurrent(id);
      });
    }
    card.querySelectorAll("[data-poll]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await fetch(`/api/poll/${btn.dataset.poll}`, { method: "POST" });
        refreshCurrent(id);
      });
    });
  });
}

function refreshCurrent(id) {
  if (stage.dataset.page === "post") loadThread(id);
  else loadFeed();
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("'", "&#39;");
}
