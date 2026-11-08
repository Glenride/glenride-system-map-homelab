/* Glenride System Map — vanilla frontend. Fetches cards from /api/cards,
   renders them per tab, and PUTs edits back. All user content is escaped. */
(function () {
  "use strict";

  var SECTION_META = {
    leadership: {
      note: "The chain, top to bottom. Click any card to edit titles, responsibilities, and notes.",
      layout: "chain"
    },
    departments: {
      note: "Seven departments, each a cost center. Every card carries its bridge: what exists today, and what it is becoming.",
      layout: "dept-grid"
    },
    budget: {
      note: "The annual budget cycle — planned a year ahead, tracked to completion, leftovers reallocated.",
      layout: "flow"
    },
    structure: {
      note: "How money moves, and the walls that hold it all.",
      layout: "wide-grid"
    }
  };

  var BRIDGE_LABELS = ["Today — what exists now", "Becoming — the vision"];

  var board = document.getElementById("board");
  var toast = document.getElementById("toast");
  var cardsBySection = {};
  var activeSection = "leadership";
  var editingId = null;

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function paragraphs(text) {
    return String(text == null ? "" : text)
      .split(/\n{2,}|\n/)
      .filter(function (p) { return p.trim().length > 0; })
      .map(function (p) { return "<p>" + esc(p) + "</p>"; })
      .join("");
  }

  function showToast(msg, isError) {
    toast.textContent = msg;
    toast.classList.toggle("error", !!isError);
    toast.hidden = false;
    clearTimeout(showToast._t);
    showToast._t = setTimeout(function () { toast.hidden = true; }, 2600);
  }

  function fmtDate(iso) {
    try {
      return new Date(iso).toLocaleString();
    } catch (e) {
      return iso;
    }
  }

  function fieldView(label, value, bridgeClass) {
    var cls = bridgeClass ? ' class="' + bridgeClass + '"' : "";
    return (
      '<div class="field"' + cls + ">" +
      '<div class="field-label">' + esc(label) + "</div>" +
      '<div class="field-value">' + (paragraphs(value) || '<p style="color:#9ca3af">—</p>') + "</div>" +
      "</div>"
    );
  }

  function fieldEdit(label, value) {
    return (
      '<div class="field">' +
      '<div class="field-label">' + esc(label) + "</div>" +
      '<textarea data-field="' + esc(label) + '">' + esc(value) + "</textarea>" +
      "</div>"
    );
  }

  function renderCard(card, layout) {
    var html = "";
    var cardClass = "card" + (layout === "chain" ? " chain-card" : layout === "flow" ? " flow-card" : "");
    html += '<article class="' + cardClass + '" data-id="' + esc(card.id) + '">';
    html += '<div class="card-head"><h2>' + esc(card.title) + "</h2>";

    if (editingId === card.id) {
      html += "</div>";
      var labels = Object.keys(card.fields);
      labels.forEach(function (label) {
        html += fieldEdit(label, card.fields[label]);
      });
      html += '<div class="btn-row">' +
        '<button class="btn primary" data-action="save">Save</button>' +
        '<button class="btn" data-action="cancel">Cancel</button>' +
        "</div>";
    } else {
      html += '<button class="btn" data-action="edit">Edit</button></div>';
      var labels = Object.keys(card.fields);
      // Bridge pair renders side-by-side when both present.
      var today = card.fields[BRIDGE_LABELS[0]];
      var becoming = card.fields[BRIDGE_LABELS[1]];
      labels.forEach(function (label) {
        if (label === BRIDGE_LABELS[0] || label === BRIDGE_LABELS[1]) return;
        html += fieldView(label, card.fields[label]);
      });
      if (today !== undefined || becoming !== undefined) {
        html += '<div class="bridge">' +
          fieldView(BRIDGE_LABELS[0], today || "", "bridge-today") +
          fieldView(BRIDGE_LABELS[1], becoming || "", "bridge-becoming") +
          "</div>";
      }
      html += '<div class="updated">Last updated ' + esc(fmtDate(card.updated_at)) + "</div>";
    }

    html += "</article>";
    return html;
  }

  function render() {
    var meta = SECTION_META[activeSection];
    var cards = (cardsBySection[activeSection] || []).slice().sort(function (a, b) {
      return a.ord - b.ord;
    });
    var html = '<p class="section-note">' + esc(meta.note) + "</p>";
    html += '<div class="' + meta.layout + '">';
    cards.forEach(function (card) {
      html += renderCard(card, meta.layout);
    });
    html += "</div>";
    board.innerHTML = html;
  }

  function findCard(id) {
    var all = [];
    Object.keys(cardsBySection).forEach(function (s) {
      all = all.concat(cardsBySection[s]);
    });
    for (var i = 0; i < all.length; i++) {
      if (all[i].id === id) return all[i];
    }
    return null;
  }

  function collectEdits(article) {
    var fields = {};
    var areas = article.querySelectorAll("textarea[data-field]");
    for (var i = 0; i < areas.length; i++) {
      fields[areas[i].getAttribute("data-field")] = areas[i].value;
    }
    return fields;
  }

  board.addEventListener("click", function (ev) {
    var btn = ev.target.closest("button[data-action]");
    if (!btn) return;
    var article = ev.target.closest("article[data-id]");
    if (!article) return;
    var id = article.getAttribute("data-id");
    var action = btn.getAttribute("data-action");

    if (action === "edit") {
      editingId = id;
      render();
      var first = article.querySelector("textarea");
      if (first) first.focus();
    } else if (action === "cancel") {
      editingId = null;
      render();
    } else if (action === "save") {
      var fields = collectEdits(article);
      btn.disabled = true;
      btn.textContent = "Saving…";
      fetch("/api/cards/" + encodeURIComponent(id), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fields: fields })
      })
        .then(function (resp) {
          if (!resp.ok) throw new Error("save failed (" + resp.status + ")");
          return resp.json();
        })
        .then(function (data) {
          var card = findCard(id);
          if (card && data.card) {
            card.fields = data.card.fields;
            card.updated_at = data.card.updated_at;
          }
          editingId = null;
          render();
          showToast("Saved.");
        })
        .catch(function (err) {
          btn.disabled = false;
          btn.textContent = "Save";
          showToast("Could not save: " + err.message, true);
        });
    }
  });

  document.querySelectorAll(".tab").forEach(function (tab) {
    tab.addEventListener("click", function () {
      document.querySelectorAll(".tab").forEach(function (t) {
        t.classList.remove("active");
      });
      tab.classList.add("active");
      activeSection = tab.getAttribute("data-section");
      editingId = null;
      render();
    });
  });

  fetch("/api/cards")
    .then(function (resp) {
      if (!resp.ok) throw new Error("could not load cards (" + resp.status + ")");
      return resp.json();
    })
    .then(function (data) {
      cardsBySection = {};
      (data.cards || []).forEach(function (card) {
        (cardsBySection[card.section] = cardsBySection[card.section] || []).push(card);
      });
      render();
    })
    .catch(function (err) {
      board.innerHTML = '<p class="loading">Could not load the map: ' + esc(err.message) + "</p>";
    });
})();
