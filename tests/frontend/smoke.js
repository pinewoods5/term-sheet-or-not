/* Frontend smoke test. Assembled and run by tests/test_frontend.py.

   Guards the things that would leave a founder looking at a black rectangle:
   that boot actually paints, that clicking a mode card advances, that the
   results renderer survives a real payload, and that nothing loops. */

const failures = [];
function check(label, condition) {
  if (!condition) failures.push(label);
}

/* --- 1. boot paints the landing screen --- */
boot();

/* Drain the microtask queue boot() awaits on, then assert. */
let chain = Promise.resolve();
for (let i = 0; i < 40; i++) chain = chain.then(() => {});

chain
  .then(() => {
    check("boot renders something into #app", ROOT.childNodes.length > 0);

    const cards = ROOT.findAll((n) => n.hasClass("mode-card"));
    check("landing renders both mode cards, got " + cards.length, cards.length === 2);
    check(
      "landing shows the operator pitch",
      ROOT.textContent.indexOf("I already built this thing") !== -1
    );
    check(
      "landing shows the scout pitch",
      ROOT.textContent.indexOf("Should I even build this thing") !== -1
    );
    check("boot did not loop, fetches=" + FETCHES.length, FETCHES.length <= 6);

    /* --- 2. clicking a card advances to the form --- */
    if (cards.length) {
      cards[0].click();
      check("clicking a mode card renders the form", ROOT.findAll((n) => n.hasClass("field")).length > 0);
      check(
        "form shows step 1 of the operator flow",
        ROOT.textContent.indexOf("The basics") !== -1
      );
      check("form renders a progress bar", ROOT.findAll((n) => n.hasClass("dot")).length === 5);

      /* required fields empty -> next is disabled */
      const next = ROOT.find((n) => n.attributes.id === "next-btn");
      check("next is disabled until required fields are filled", next && next.attributes.disabled);
    }

    /* --- 3. the results renderer survives a real payload --- */
    go("results", { result: RESULT });
    check("results render the verdict tier", ROOT.textContent.indexOf(RESULT.tier.label) !== -1);
    check("results render the headline", ROOT.textContent.indexOf(RESULT.headline) !== -1);
    check(
      "results render one post per category, got " +
        ROOT.findAll((n) => n.hasClass("cat-head")).length,
      ROOT.findAll((n) => n.hasClass("cat-head")).length === RESULT.categories.length
    );
    check("results render three ranked fixes", ROOT.findAll((n) => n.hasClass("fix")).length === 3);
    check(
      "results render the research links",
      ROOT.textContent.indexOf(RESULT.research_notes[0].finding) !== -1
    );

    console.log(failures.length ? "FAIL\n" + failures.join("\n") : "PASS");
  })
  .catch((e) => console.log("FAIL\nthrew: " + (e && e.message ? e.message : e)));
