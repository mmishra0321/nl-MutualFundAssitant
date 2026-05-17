(function () {
  "use strict";

  var API_BASE =
    typeof window.MS02_API_BASE === "string" ? window.MS02_API_BASE.replace(/\/$/, "") : "";

  var form = document.getElementById("ask-form");
  var input = document.getElementById("question-input");
  var submitBtn = document.getElementById("submit-btn");
  var statusEl = document.getElementById("status");
  var welcomeScreen = document.getElementById("welcome-screen");
  var messagesEl = document.getElementById("messages");
  var newChatBtn = document.getElementById("new-chat-btn");
  var clearChatsBtn = document.getElementById("clear-chats-btn");
  var historyList = document.getElementById("history-list");
  var chatTitleEl = document.getElementById("chat-title");
  var chatBody = document.getElementById("chat-body");

  var store = {
    nextId: 2,
    activeId: "1",
    chats: [
      {
        id: "1",
        title: "Chat 1",
        messages: [],
      },
    ],
  };

  function getActiveChat() {
    for (var i = 0; i < store.chats.length; i++) {
      if (store.chats[i].id === store.activeId) return store.chats[i];
    }
    return store.chats[0];
  }

  function setStatus(msg, isError) {
    statusEl.textContent = msg || "";
    statusEl.classList.toggle("error", Boolean(isError));
  }

  function scrollToBottom() {
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  function truncateTitle(text, max) {
    var t = (text || "").replace(/\s+/g, " ").trim();
    if (t.length <= max) return t;
    return t.slice(0, max - 1) + "…";
  }

  function maybeRenameChatFromQuestion(chat, question) {
    if (chat.messages.length === 0 && /^Chat \d+$/.test(chat.title)) {
      chat.title = truncateTitle(question, 36) || chat.title;
    }
  }

  function renderMessages(chat) {
    messagesEl.innerHTML = "";
    chat.messages.forEach(function (m) {
      var wrap = document.createElement("div");
      wrap.className = "msg msg-" + m.role;
      var bubble = document.createElement("div");
      bubble.className = "msg-bubble";
      bubble.textContent = m.text;
      wrap.appendChild(bubble);
      if (m.metaHtml) {
        var meta = document.createElement("div");
        meta.className = "msg-meta";
        meta.innerHTML = m.metaHtml;
        wrap.appendChild(meta);
      }
      messagesEl.appendChild(wrap);
    });
  }

  function renderActiveView() {
    var chat = getActiveChat();
    chatTitleEl.textContent = chat.title;

    if (chat.messages.length === 0) {
      welcomeScreen.classList.remove("hidden");
      messagesEl.hidden = true;
      messagesEl.innerHTML = "";
    } else {
      welcomeScreen.classList.add("hidden");
      messagesEl.hidden = false;
      renderMessages(chat);
    }
    scrollToBottom();
  }

  function renderHistory() {
    historyList.innerHTML = "";
    store.chats.forEach(function (chat) {
      var li = document.createElement("li");
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "history-item" + (chat.id === store.activeId ? " active" : "");
      btn.setAttribute("data-chat-id", chat.id);

      var icon = document.createElement("span");
      icon.className = "history-icon";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = "💬";

      var labelWrap = document.createElement("span");
      labelWrap.className = "history-item-text";
      var titleSpan = document.createElement("span");
      titleSpan.className = "history-item-title";
      titleSpan.textContent = chat.title;
      labelWrap.appendChild(titleSpan);

      if (chat.messages.length > 0) {
        var preview = document.createElement("span");
        preview.className = "history-item-preview";
        var last = chat.messages[chat.messages.length - 1];
        preview.textContent =
          last.role === "user"
            ? truncateTitle(last.text, 42)
            : truncateTitle(last.text, 42);
        labelWrap.appendChild(preview);
      }

      btn.appendChild(icon);
      btn.appendChild(labelWrap);
      btn.addEventListener("click", function () {
        switchChat(chat.id);
      });

      li.appendChild(btn);
      historyList.appendChild(li);
    });
  }

  function switchChat(chatId) {
    if (chatId === store.activeId) return;
    store.activeId = chatId;
    setStatus("");
    input.value = "";
    renderHistory();
    renderActiveView();
    input.focus();
  }

  function createNewChat() {
    var id = String(store.nextId++);
    var labelNum = store.chats.length + 1;
    store.chats.unshift({
      id: id,
      title: "Chat " + labelNum,
      messages: [],
    });
    store.activeId = id;
    setStatus("");
    input.value = "";
    renderHistory();
    renderActiveView();
    input.focus();
  }

  function clearAllChats() {
    var msg =
      "Clear all chats? Every conversation in the sidebar will be removed. This cannot be undone.";
    if (!window.confirm(msg)) return;

    store.nextId = 2;
    store.activeId = "1";
    store.chats = [
      {
        id: "1",
        title: "Chat 1",
        messages: [],
      },
    ];
    setStatus("");
    input.value = "";
    renderHistory();
    renderActiveView();
    input.focus();
  }

  function appendMessage(role, text, metaHtml) {
    var chat = getActiveChat();
    chat.messages.push({ role: role, text: text, metaHtml: metaHtml || "" });

    welcomeScreen.classList.add("hidden");
    messagesEl.hidden = false;

    var wrap = document.createElement("div");
    wrap.className = "msg msg-" + role;
    var bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.textContent = text;
    wrap.appendChild(bubble);
    if (metaHtml) {
      var meta = document.createElement("div");
      meta.className = "msg-meta";
      meta.innerHTML = metaHtml;
      wrap.appendChild(meta);
    }
    messagesEl.appendChild(wrap);
    scrollToBottom();
    renderHistory();
  }

  function appendLoading() {
    welcomeScreen.classList.add("hidden");
    messagesEl.hidden = false;
    var wrap = document.createElement("div");
    wrap.className = "msg msg-assistant msg-loading";
    var bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.textContent = "Looking up verified fund data…";
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    scrollToBottom();
  }

  function removeLoading() {
    var el = messagesEl.querySelector(".msg-loading");
    if (el) el.remove();
  }

  function buildMeta(data) {
    var parts = [];
    if (data.source_url) {
      parts.push(
        'Source: <a href="' +
          encodeURI(data.source_url) +
          '" target="_blank" rel="noopener noreferrer">Official scheme page</a>'
      );
    }
    if (data.last_updated) {
      parts.push("Last updated from sources: " + data.last_updated);
    }
    return parts.join(" · ");
  }

  function formatDetail(body) {
    if (!body) return "";
    var d = body.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) {
      return d
        .map(function (x) {
          return (x && x.msg) || JSON.stringify(x);
        })
        .join(" ");
    }
    if (d && typeof d === "object") return JSON.stringify(d);
    return String(body.message || "");
  }

  function submitQuestion(question) {
    var q = (question || "").trim();
    if (!q) {
      setStatus("Please enter a question.", true);
      return;
    }

    var chat = getActiveChat();
    maybeRenameChatFromQuestion(chat, q);
    renderHistory();
    chatTitleEl.textContent = chat.title;

    appendMessage("user", q);
    input.value = "";
    submitBtn.disabled = true;
    setStatus("");
    appendLoading();

    fetch(API_BASE + "/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ question: q }),
    })
      .then(function (res) {
        return res.text().then(function (text) {
          var body = null;
          if (text) {
            try {
              body = JSON.parse(text);
            } catch (e) {
              body = { detail: text.slice(0, 280) };
            }
          }
          return { ok: res.ok, status: res.status, body: body };
        });
      })
      .then(function (r) {
        removeLoading();
        if (!r.ok) {
          throw new Error(formatDetail(r.body) || "Request failed (" + r.status + ")");
        }
        appendMessage("assistant", r.body.answer || "", buildMeta(r.body));
      })
      .catch(function (err) {
        removeLoading();
        appendMessage("assistant", err.message || "Something went wrong.", "");
        setStatus("", true);
      })
      .finally(function () {
        submitBtn.disabled = false;
        input.focus();
      });
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    submitQuestion(input.value);
  });

  document.querySelectorAll(".suggestion-card").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var q = btn.getAttribute("data-question") || "";
      input.value = q;
      submitQuestion(q);
    });
  });

  newChatBtn.addEventListener("click", createNewChat);
  clearChatsBtn.addEventListener("click", clearAllChats);

  renderHistory();
  renderActiveView();
  input.focus();
})();
