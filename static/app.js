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
  error: null,
};

function go(screen, patch) {
  Object.assign(state, patch || {}, { screen });
  /* ---------- boot ---------- */

fetch("/api/forms")
  .then((r) => r.json())
  .then((f) => {
    FORMS = f;
    render();
  })
  .catch(() => {
    app.replaceChildren(
      h("p", { class: "empty" }, "Couldn't load the questions. Is the server running?")
    );
  });
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
      h("p", { class: "empty" }, "Nothing yet. Go get told.")
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

function submit() {
  go("loading");
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
    default:
      nodes = landing();
  }
  app.append(...[nodes].flat());
  window.scrollTo(0, 0);
}

/* ---------- boot ---------- */

fetch("/api/forms")
  .then((r) => r.json())
  .then((f) => {
    FORMS = f;
    render();
  })
  .catch(() => {
    app.replaceChildren(
      h("p", { class: "empty" }, "Couldn't load the questions. Is the server running?")
    );
  });
