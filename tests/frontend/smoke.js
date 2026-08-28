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

    /* --- 2. the operator card is locked, the scout card never is --- */
    check("operator card renders locked", cards[0].hasClass("locked"));
    check("scout card is not locked", !cards[1].hasClass("locked"));
    check("locked card explains itself", cards[0].textContent.indexOf("access key") !== -1);
    check("tiers are labelled", ROOT.textContent.indexOf("Premium") !== -1 &&
      ROOT.textContent.indexOf("Free") !== -1);

    cards[0].click();
    check("clicking the locked operator opens the key prompt",
      ROOT.textContent.indexOf("This one needs a key") !== -1);
    check("key prompt does not render the form",
      ROOT.findAll((n) => n.hasClass("field")).length === 0);

    /* --- 3. scout reaches its form with no key and no access call --- */
    go("landing", {});
    const scoutCard = ROOT.findAll((n) => n.hasClass("mode-card"))[1];
    scoutCard.click();
    check("scout opens its form without any key", ROOT.findAll((n) => n.hasClass("field")).length > 0);
    check("scout form starts at its own first step",
      ROOT.textContent.indexOf("The idea") !== -1);
    check("scout progress bar has four steps",
      ROOT.findAll((n) => n.hasClass("dot")).length === 4);
    const scoutNext = ROOT.find((n) => n.attributes.id === "next-btn");
    check("next is disabled until required fields are filled",
      scoutNext && scoutNext.attributes.disabled);

    /* --- 4. an unlocked operator behaves normally --- */
    state.access.operator = true;
    go("landing", {});
    const unlocked = ROOT.findAll((n) => n.hasClass("mode-card"));
    check("unlocked operator card loses the lock", !unlocked[0].hasClass("locked"));
    unlocked[0].click();
    check("unlocked operator opens its form",
      ROOT.textContent.indexOf("The basics") !== -1);
    check("operator progress bar has five steps",
      ROOT.findAll((n) => n.hasClass("dot")).length === 5);

    /* --- 5. the results renderer survives a real payload --- */
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
