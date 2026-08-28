/* A DOM stub just large enough to run static/app.js outside a browser.

   There is no Node on this machine and no browser automation in the loop, so
   the frontend would otherwise ship completely unexercised -- which is exactly
   how a blank page reached a browser once already. This runs under macOS's
   built-in JavaScriptCore (osascript -l JavaScript).

   It implements only what app.js actually touches. If app.js starts using
   something new, this throws rather than silently pretending. */

class Node {
  constructor(tag) {
    this.tagName = (tag || "").toUpperCase();
    this.childNodes = [];
    this.attributes = {};
    this.listeners = {};
    this.className = "";
    this._text = "";
  }
  get textContent() {
    return this._text + this.childNodes.map((c) => c.textContent).join("");
  }
  set innerHTML(v) {
    this._html = v;
  }
  get innerHTML() {
    return this._html || "";
  }
  setAttribute(k, v) {
    this.attributes[k] = String(v);
  }
  getAttribute(k) {
    return this.attributes[k];
  }
  addEventListener(type, fn) {
    (this.listeners[type] = this.listeners[type] || []).push(fn);
  }
  append(...kids) {
    for (const k of kids) this.childNodes.push(k);
  }
  replaceChildren(...kids) {
    this.childNodes = [];
    this.append(...kids);
  }
  scrollIntoView() {}
  click() {
    for (const fn of this.listeners.click || []) fn({ target: this });
  }
  /* test helpers */
  find(pred) {
    if (pred(this)) return this;
    for (const c of this.childNodes) {
      const hit = c.find ? c.find(pred) : null;
      if (hit) return hit;
    }
    return null;
  }
  findAll(pred, out) {
    out = out || [];
    if (pred(this)) out.push(this);
    for (const c of this.childNodes) if (c.findAll) c.findAll(pred, out);
    return out;
  }
  hasClass(name) {
    return String(this.className).split(/\s+/).indexOf(name) !== -1;
  }
}

class TextNode extends Node {
  constructor(text) {
    super("#text");
    this._text = String(text);
  }
}

const ROOT = new Node("main");
ROOT.attributes.id = "app";
const BODY = new Node("body");

const document = {
  getElementById: (id) => (id === "app" ? ROOT : null),
  createElement: (tag) => new Node(tag),
  createTextNode: (t) => new TextNode(t),
  body: BODY,
};

const window = {
  location: { pathname: "/" },
  addEventListener: () => {},
  scrollTo: () => {},
};

const history = { pushState: () => {} };
const navigator = { clipboard: { writeText: () => {} } };
const setTimeout = (fn) => fn;

/* fetch, counted -- a runaway boot loop shows up here as a huge number */
const FETCHES = [];
function fetch(url) {
  FETCHES.push(url);
  if (FETCHES.length > 200) throw new Error("runaway fetch loop: " + FETCHES.length);
  const data = FIXTURES[url];
  if (data === undefined) throw new Error("stub has no fixture for " + url);
  return Promise.resolve({ ok: true, json: () => Promise.resolve(data) });
}
