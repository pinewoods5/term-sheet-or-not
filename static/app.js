/* Term Sheet or Not — frontend.
   No framework. A tiny element helper, a screen router, and one state object.
   Everything user-typed goes through h()/text nodes, never innerHTML, so a
   founder who types HTML into a form field gets roasted, not executed. */

const app = document.getElementById("app");

/* ---------- dom helper ---------- */

function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v; // only for our own inline svg
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

const VERIFIED_SVG =
  '<svg class="verified" viewBox="0 0 22 22" aria-label="Verified">' +
  '<path d="M20.396 11c-.018-.646-.215-1.275-.57-1.816-.354-.54-.852-.972-1.438-1.246.223-.607.27-1.264.14-1.897-.131-.634-.437-1.218-.882-1.687-.47-.445-1.053-.75-1.687-.882-.633-.13-1.29-.083-1.897.14-.273-.587-.704-1.086-1.245-1.44S11.647 1.62 11 1.604c-.646.017-1.273.213-1.813.568s-.969.854-1.24 1.44c-.608-.223-1.267-.272-1.902-.14-.635.13-1.22.436-1.69.882-.445.47-.749 1.055-.878 1.688-.13.633-.08 1.29.144 1.896-.587.274-1.087.705-1.443 1.245-.356.54-.555 1.17-.574 1.817.02.647.218 1.276.574 1.817.356.54.856.972 1.443 1.245-.224.606-.274 1.263-.144 1.896.13.634.433 1.218.877 1.688.47.443 1.054.747 1.687.878.633.132 1.29.084 1.897-.136.274.586.705 1.084 1.246 1.439.54.354 1.17.551 1.816.569.647-.016 1.276-.213 1.817-.567s.972-.854 1.245-1.44c.604.239 1.266.296 1.903.164.636-.132 1.22-.447 1.68-.907.46-.46.776-1.044.908-1.681s.075-1.299-.165-1.903c.586-.274 1.084-.705 1.439-1.246.354-.54.551-1.17.569-1.816zM9.662 14.85l-3.429-3.428 1.293-1.302 2.072 2.072 4.4-4.794 1.347 1.246z"/>' +
  "</svg>";

function verified() {
  return h("span", { class: "check", html: VERIFIED_SVG });
}

/* ---------- state ---------- */

const state = {
  screen: "landing", // landing | form | loading | results
  mode: null, // operator | scout
  step: 0,
  answers: {},
  result: null,
  status: null,
  error: null,
  history: [],
};

function go(screen, patch) {
  Object.assign(state, patch || {}, { screen });
  render();
}

let FORMS = null; // fetched from /api/forms at boot

/* ---------- modes ---------- */

const MODES = {
  operator: {
    handle: "the_operator",
    name: "The Operator",
    emoji: "\u{1F4C9}",
    pitch: "I already built this thing",
    desc:
      "Revenue, retention, burn, runway, team, moat. The whole business, judged " +
      "on what it actually does — not what the deck says it will.",
  },
  scout: {
    handle: "the_scout",
    name: "The Scout",
    emoji: "\u{1F52D}",
    pitch: "Should I even build this thing",
    desc:
      "No revenue to hide behind. Just you, the idea, and whether you're the " +
      "right person to be the one who builds it.",
  },
};

/* ---------- screens ---------- */

function topbar(title, sub, onBack) {
  return h(
    "header",
    { class: "topbar" },
    onBack && h("button", { class: "back", onclick: onBack, "aria-label": "Back" }, "←"),
    h("div", {}, h("h1", {}, title), sub && h("div", { class: "sub" }, sub))
  );
}

function landing() {
  const cards = Object.entries(MODES).map(([key, m]) =>
    h(
      "button",
      { class: "mode-card", onclick: () => go("form", { mode: key, answers: {}, step: 0 }) },
      h(
        "div",
        { class: "who" },
        h("div", { class: "avatar" }, m.emoji),
        h("span", { class: "name" }, m.name),
        verified(),
        h("span", { class: "at" }, "@" + m.handle)
      ),
      h("p", { class: "pitch" }, m.pitch),
      h("p", { class: "desc" }, m.desc)
    )
  );

  return [
    topbar("Term Sheet or Not", "Two VCs. No participation trophies."),
    h(
      "section",
      { class: "hero" },
      h("h2", {}, "Which one of us is judging you today?"),
      h(
        "p",
        {},
        "Pick the evaluator that matches where you actually are. They ask " +
          "different questions and score on different rubrics, because a " +
          "company with customers and an idea in a notes app are not the " +
          "same animal."
      )
    ),
    h("div", { class: "mode-grid" }, cards),
    h(
      "section",
      { class: "section" },
      h("p", { class: "section-label" }, "Recent verdicts"),
      state.history.length
        ? state.history.map((row) =>
            h(
              "button",
              { class: "history-item", onclick: () => openResult(row.id) },
              h("div", { class: "avatar" }, MODES[row.mode].emoji),
              h(
                "div",
                {},
                h("div", { class: "h-name" }, row.subject),
                h("div", { class: "h-meta" }, row.tier + " · " + row.overall + "/100 · " + shortTime(row.created_at))
              )
            )
          )
        : h("p", { class: "empty" }, "Nothing yet. Go get told."),
    ),
  ];
}

/* ---------- form engine ---------- */

function stepFields(mode, step) {
  return FORMS[mode].steps[step].fields;
}

function stepIsSatisfied(mode, step) {
  return stepFields(mode, step)
    .filter((f) => f.required)
    .every((f) => (state.answers[f.k] || "").trim().length > 0);
}

function fieldNode(f) {
  const id = "f_" + f.k;
  const value = state.answers[f.k] || "";
  const common = {
    id,
    name: f.k,
    placeholder: f.ph || "",
    oninput: (e) => {
      state.answers[f.k] = e.target.value;
      if (f.required) refreshNav();
    },
  };

  let input;
  if (f.type === "textarea") {
    input = h("textarea", { ...common, rows: 3 }, value);
  } else if (f.type === "select") {
    input = h(
      "select",
      {
        ...common,
        onchange: (e) => {
          state.answers[f.k] = e.target.value;
          if (f.required) refreshNav();
        },
      },
      f.options.map((o) =>
        h("option", { value: o, selected: o === value || null }, o || "—")
      )
    );
  } else {
    input = h("input", { ...common, type: "text", value, autocomplete: "off" });
  }

  return h(
    "div",
    { class: "field" },
    h(
      "label",
      { for: id },
      f.label,
      !f.required && h("span", { class: "optional" }, "  optional")
    ),
    f.hint && h("span", { class: "hint" }, f.hint),
    input
  );
}

function refreshNav() {
  const btn = document.getElementById("next-btn");
  if (btn) btn.disabled = !stepIsSatisfied(state.mode, state.step);
}

function advance() {
  if (!stepIsSatisfied(state.mode, state.step)) return;
  const last = FORMS[state.mode].steps.length - 1;
  if (state.step < last) go("form", { step: state.step + 1 });
  else submit();
}

function retreat() {
  if (state.step > 0) go("form", { step: state.step - 1 });
  else go("landing", { mode: null, step: 0 });
}

function formScreen() {
  const mode = MODES[state.mode];
  const form = FORMS[state.mode];
  const step = form.steps[state.step];
  const last = state.step === form.steps.length - 1;

  const dots = form.steps.map((_, i) =>
    h("div", { class: "dot" + (i <= state.step ? " done" : "") })
  );

  return [
    topbar(mode.name, "Step " + (state.step + 1) + " of " + form.steps.length, retreat),
    h("div", { class: "progress" }, dots),
    h(
      "div",
      { class: "step-head" },
      h("h2", {}, step.title),
      h("p", {}, step.blurb)
    ),
    h(
      "form",
      {
        class: "fields",
        onsubmit: (e) => {
          e.preventDefault();
          advance();
        },
        onkeydown: (e) => {
          if (e.key !== "Enter") return;
          const isTextarea = e.target.tagName === "TEXTAREA";
          if (isTextarea && !(e.metaKey || e.ctrlKey)) return;
          e.preventDefault();
          advance();
        },
      },
      step.fields.map(fieldNode),
      h("button", { type: "submit", style: "display:none" })
    ),
    h(
      "div",
      { class: "step-nav" },
      h("button", { class: "btn btn-ghost", onclick: retreat }, state.step === 0 ? "Back out" : "Back"),
      h("span", { class: "spacer" }),
      h("span", { class: "keyhint" }, last ? "⌘↩ to submit" : "↩ for next"),
      h(
        "button",
        {
          id: "next-btn",
          class: "btn btn-primary",
          disabled: !stepIsSatisfied(state.mode, state.step) || null,
          onclick: advance,
        },
        last ? form.submitLabel : "Next"
      )
    ),
  ];
}

/* ---------- submitting ---------- */

async function submit() {
  go("loading", { status: "Sending this to someone who won't be kind.", error: null });

  let response;
  try {
    response = await fetch("/api/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: state.mode, answers: state.answers }),
    });
  } catch (e) {
    return go("loading", { error: "Couldn't reach the server." });
  }

  if (!response.ok || !response.body) {
    const detail = await response.text().catch(() => "");
    return go("loading", { error: detail || "The server refused that submission." });
  }

  // Minimal SSE reader. EventSource can't POST, and the submission is too big
  // to sit in a query string, so we parse the stream ourselves.
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let split;
    while ((split = buffer.indexOf("\n\n")) !== -1) {
      const chunk = buffer.slice(0, split);
      buffer = buffer.slice(split + 2);

      const event = (chunk.match(/^event: (.*)$/m) || [])[1];
      const dataLine = (chunk.match(/^data: (.*)$/m) || [])[1];
      if (!event || !dataLine) continue;
      const data = JSON.parse(dataLine);

      if (event === "status") go("loading", { status: data.text });
      else if (event === "error") go("loading", { error: data.message });
      else if (event === "result") {
        history.pushState({}, "", "/r/" + data.id);
        return go("results", { result: data });
      }
    }
  }

  if (state.screen === "loading" && !state.error) {
    go("loading", { error: "The stream ended without a verdict. Try again." });
  }
}

function loadingScreen() {
  if (state.error) {
    return [
      topbar(MODES[state.mode] ? MODES[state.mode].name : "Term Sheet or Not", null, () =>
        go("form", { error: null })
      ),
      h(
        "div",
        { class: "loading" },
        h("p", { class: "status" }, "That didn't work."),
        h("p", { class: "sub" }, state.error),
        h(
          "div",
          { class: "actions" },
          h("button", { class: "btn btn-primary", onclick: submit }, "Try again"),
          h("button", { class: "btn", onclick: () => go("form", { error: null }) }, "Edit answers")
        )
      ),
    ];
  }

  return [
    topbar(MODES[state.mode].name, "Evaluating"),
    h(
      "div",
      { class: "loading" },
      h("div", { class: "spinner" }),
      h("p", { class: "status" }, state.status || "Thinking."),
      h(
        "p",
        { class: "sub" },
        state.mode === "operator"
          ? "This takes 30-60 seconds. It's reading the market, not stalling."
          : "This takes 20-40 seconds. It's thinking, not stalling."
      )
    ),
  ];
}

/* ---------- results ---------- */

function scoreClass(score) {
  if (score >= 8) return "score-pill score-good";
  if (score <= 3) return "score-pill score-bad";
  return "score-pill score-mid";
}

function shortTime(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function postHead(mode, time) {
  return h(
    "div",
    { class: "post-head" },
    h("span", { class: "name" }, mode.name),
    verified(),
    h("span", { class: "handle" }, "@" + mode.handle),
    time && h("span", { class: "time" }, "· " + shortTime(time))
  );
}

function toast(message) {
  const node = h("div", { class: "toast" }, message);
  document.body.append(node);
  setTimeout(() => node.remove(), 1800);
}

function engageRow(result) {
  return h(
    "div",
    { class: "engage" },
    h(
      "button",
      {
        onclick: () => document.getElementById("fix-first").scrollIntoView({ behavior: "smooth" }),
        title: "Jump to what to fix",
      },
      "↩ fix this first"
    ),
    h("button", { onclick: rerun, title: "Edit your answers and run it again" }, "↻ re-run"),
    h("button", { disabled: true }, "♡ " + result.overall_score + "/100"),
    h(
      "button",
      {
        onclick: () => {
          navigator.clipboard.writeText(window.location.href);
          toast("Link copied");
        },
      },
      "↗ copy link"
    )
  );
}

function rerun() {
  go("form", { mode: state.result.mode, answers: { ...state.result.answers }, step: 0 });
  history.pushState({}, "", "/");
}

function verdictPost(result, mode) {
  const tier = result.tier;
  return [
    h("div", { class: "pin-label" }, "📌 Pinned verdict"),
    h(
      "article",
      { class: "post" },
      h("div", { class: "rail" }, h("div", { class: "avatar" }, mode.emoji), h("div", { class: "line" })),
      h(
        "div",
        { class: "post-body" },
        postHead(mode, result.created_at),
        h(
          "div",
          { class: "verdict tone-" + tier.tone },
          h("p", { class: "tier" }, tier.label),
          h("p", { class: "score" }, result.overall_score + " / 100 — weighted across " + result.categories.length + " categories"),
          h("p", { class: "blurb" }, tier.blurb)
        ),
        h("p", { class: "headline" }, result.headline),
        h("p", {}, result.thesis),
        engageRow(result)
      )
    ),
  ];
}

function categoryPost(category, mode) {
  return h(
    "article",
    { class: "post" },
    h(
      "div",
      { class: "rail" },
      h("div", { class: "avatar" }, mode.emoji),
      h("div", { class: "line" })
    ),
    h(
      "div",
      { class: "post-body" },
      postHead(mode),
      h(
        "div",
        { class: "cat-head" },
        h("span", { class: "label" }, category.label),
        h("span", { class: scoreClass(category.score) }, category.score + "/10"),
        h("span", { class: "weight" }, Math.round(category.weight * 100) + "% of the score")
      ),
      h("p", { class: "cat-verdict" }, category.verdict),
      h("p", {}, category.reasoning)
    )
  );
}

function flagList(items, kind) {
  return h(
    "ul",
    { class: "flags " + (kind === "good" ? "good" : "bad") },
    items.map((item) =>
      h("li", {}, h("span", { class: "mark" }, kind === "good" ? "+" : "−"), h("span", {}, item))
    )
  );
}

function resultsScreen() {
  const result = state.result;
  const mode = MODES[result.mode];
  const subject =
    (result.answers && (result.answers.company_name || result.answers.idea_one_liner)) || "";

  const nodes = [
    topbar(mode.name, subject, () => {
      history.pushState({}, "", "/");
      go("landing", { result: null, mode: null });
    }),
    ...verdictPost(result, mode),
    ...result.categories.map((c) => categoryPost(c, mode)),
    h(
      "section",
      { class: "section", id: "fix-first" },
      h("p", { class: "section-label" }, "Fix this first"),
      result.fix_this_first.map((fix) =>
        h(
          "div",
          { class: "fix" },
          h("div", { class: "rank" }, "#" + fix.rank),
          h("h3", {}, fix.title),
          h("p", {}, fix.why),
          h("p", { class: "do" }, h("strong", {}, "Do this: "), fix.do_this)
        )
      )
    ),
  ];

  if (result.green_flags.length) {
    nodes.push(
      h(
        "section",
        { class: "section" },
        h("p", { class: "section-label" }, "Working"),
        flagList(result.green_flags, "good")
      )
    );
  }

  nodes.push(
    h(
      "section",
      { class: "section" },
      h("p", { class: "section-label" }, "Broken"),
      flagList(result.red_flags, "bad")
    ),
    h(
      "section",
      { class: "section" },
      h("p", { class: "section-label" }, "Strategic notes"),
      result.strategic_notes.map((note) =>
        h("div", { class: "note" }, h("h4", {}, note.title), h("p", {}, note.note))
      )
    )
  );

  if (result.research_notes.length) {
    nodes.push(
      h(
        "section",
        { class: "section" },
        h("p", { class: "section-label" }, "What I found when I looked it up"),
        result.research_notes.map((note) =>
          h(
            "div",
            { class: "research" },
            h("p", { class: "claim" }, "You said: " + note.claim),
            h("p", { class: "finding" }, note.finding),
            note.source_url &&
              h("a", { href: note.source_url, target: "_blank", rel: "noreferrer noopener" }, note.source_url)
          )
        )
      )
    );
  }

  nodes.push(
    h(
      "div",
      { class: "actions" },
      h("button", { class: "btn", onclick: rerun }, "Edit answers & re-run"),
      h(
        "button",
        {
          class: "btn btn-primary",
          onclick: () => {
            history.pushState({}, "", "/");
            go("landing", { result: null, mode: null });
          },
        },
        "Judge something else"
      )
    )
  );

  return nodes;
}

/* ---------- render ---------- */

function render() {
  app.replaceChildren();
  let nodes;
  switch (state.screen) {
    case "landing":
      nodes = landing();
      break;
    case "form":
      nodes = formScreen();
      break;
    case "loading":
      nodes = loadingScreen();
      break;
    case "results":
      nodes = resultsScreen();
      break;
    default:
      nodes = landing();
  }
  app.append(...[nodes].flat());
  window.scrollTo(0, 0);
}

/* ---------- boot & routing ---------- */

async function openResult(id) {
  const response = await fetch("/api/result/" + id);
  if (!response.ok) return;
  history.pushState({}, "", "/r/" + id);
  go("results", { result: await response.json() });
}

async function loadHistory() {
  try {
    state.history = await (await fetch("/api/history")).json();
  } catch (e) {
    state.history = [];
  }
}

function routeFromPath() {
  const match = window.location.pathname.match(/^\/r\/([a-z0-9]+)$/i);
  if (match) return openResult(match[1]);
  go("landing", { result: null, mode: null });
}

window.addEventListener("popstate", routeFromPath);

async function boot() {
  try {
    FORMS = await (await fetch("/api/forms")).json();
  } catch (e) {
    return app.replaceChildren(
      h("p", { class: "empty" }, "Couldn't load the questions. Is the server running?")
    );
  }
  await loadHistory();
  routeFromPath();
}

boot();
