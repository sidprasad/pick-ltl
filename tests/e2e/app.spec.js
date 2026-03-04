const { test, expect } = require("@playwright/test");
const { installApiMocks, installSessionStorage, makeSeed, makeSession, withPair } = require("./helpers");

test("generate creates a session and advancing a vote loads the next trace pair", async ({ page }) => {
  const prompt = "Whenever the red light is on, the blue light eventually turns on.";
  const initialSeedA = makeSeed("(G (r -> (F b)))", "Whenever red, blue eventually follows.");
  const initialSeedB = makeSeed("(F r)", "Eventually red happens.");

  const initialSession = makeSession({ prompt });
  const firstPairSession = withPair(
    initialSession,
    "r;b;cycle{b}",
    "r;!b;cycle{!b}",
    ["(G (r -> (F b)))"],
    ["(F r)"]
  );
  const afterAccept = makeSession({
    prompt,
    history: [
      {
        trace: "r;b;cycle{b}",
        classification: "accept",
        matching_candidates: ["(G (r -> (F b)))"],
        source: "pair",
        timestamp: 1,
      },
    ],
    candidate_states: [
      {
        ...initialSession.candidate_states[0],
        positive_votes: 1,
      },
      {
        ...initialSession.candidate_states[1],
        negative_votes: 1,
      },
    ],
  });
  const secondPairSession = withPair(
    afterAccept,
    "b;cycle{b}",
    "!b;cycle{!b}",
    ["(F r)"],
    []
  );

  await installApiMocks(page, {
    "POST /api/seed/generate": {
      ...initialSeedA,
      seeds: [initialSeedA, initialSeedB],
    },
    "POST /api/candidates/build": initialSession,
    "POST /api/session/next-pair": [firstPairSession, secondPairSession],
    "POST /api/session/classify": afterAccept,
  });

  await page.goto("/");
  await page.locator("#promptInput").fill(prompt);
  await page.locator("#generateBtn").click();

  await expect(page.locator("#currentPrompt")).toContainText(prompt);
  await expect(page.locator("#traceA")).toContainText("r;b;cycle{b}");
  await expect(page.locator("#traceB")).toContainText("r;!b;cycle{!b}");

  await page.locator("#pairSection .vote.accept").first().click();

  await expect(page.locator("#historyList .history-item")).toHaveCount(1);
  await expect(page.locator("#historyList")).toContainText("r;b;cycle{b}");
  await expect(page.locator("#traceA")).toContainText("b;cycle{b}");
  await expect(page.locator("#traceB")).toContainText("!b;cycle{!b}");
});

test("reclassifying a history entry recalculates the session and updates the active button", async ({ page }) => {
  const session = withPair(
    makeSession({
      history: [
        {
          trace: "r;b;cycle{b}",
          classification: "accept",
          matching_candidates: ["(G (r -> (F b)))"],
          source: "pair",
          timestamp: 1,
        },
      ],
      candidate_states: [
        {
          ...makeSession().candidate_states[0],
          positive_votes: 1,
        },
        {
          ...makeSession().candidate_states[1],
          negative_votes: 1,
        },
      ],
    }),
    "b;cycle{b}",
    "!b;cycle{!b}",
    ["(F r)"],
    []
  );

  const afterReclassify = makeSession({
    history: [
      {
        trace: "r;b;cycle{b}",
        classification: "reject",
        matching_candidates: ["(G (r -> (F b)))"],
        source: "pair",
        timestamp: 2,
      },
    ],
    candidate_states: [
      {
        ...makeSession().candidate_states[0],
        negative_votes: 1,
      },
      {
        ...makeSession().candidate_states[1],
        positive_votes: 0,
      },
    ],
  });
  const recalculatedPair = withPair(
    afterReclassify,
    "r;cycle{r}",
    "!r;cycle{!r}",
    ["(F r)"],
    []
  );

  await installSessionStorage(page, session);
  await installApiMocks(page, {
    "POST /api/session/reclassify": afterReclassify,
    "POST /api/session/next-pair": recalculatedPair,
  });

  await page.goto("/");

  const firstHistoryItem = page.locator("#historyList .history-item").first();
  await firstHistoryItem.getByRole("button", { name: "Reject" }).click();

  await expect(firstHistoryItem.getByRole("button", { name: "Reject" })).toHaveClass(/active/);
  await expect(firstHistoryItem.getByRole("button", { name: "Accept" })).not.toHaveClass(/active/);
  await expect(page.locator("#traceA")).toContainText("r;cycle{r}");
});

test("single-candidate fallback shows the result state directly", async ({ page }) => {
  const prompt = "Whenever the red light is on, the blue light eventually turns on.";
  const seedA = makeSeed("(G (r -> (F b)))", "Whenever red, blue eventually follows.");
  const seedB = makeSeed("(G (r -> (F b)))", "Equivalent second interpretation.");
  const singleCandidateSession = makeSession({
    prompt,
    seed: seedA,
    seeds: [seedA, seedB],
    candidate_states: [makeSession().candidate_states[0]],
    mode: "single_candidate",
    message: "We could only get this one.",
  });

  await installApiMocks(page, {
    "POST /api/seed/generate": {
      ...seedA,
      seeds: [seedA, seedB],
      warnings: ["Only one distinct initial formula survived validation."],
    },
    "POST /api/candidates/build": singleCandidateSession,
  });

  await page.goto("/");
  await page.locator("#promptInput").fill(prompt);
  await page.locator("#generateBtn").click();

  await expect(page.locator("#resultTitle")).toContainText("We could only get this one.");
  await expect(page.locator("#resultFormula")).toContainText("(G (r -> (F b)))");
  await expect(page.locator("#resultMessage")).toContainText("We could only get this one.");
});

test("build a new formula clears the current session and returns to prompt mode", async ({ page }) => {
  const session = makeSession({
    mode: "single_candidate",
    message: "We could only get this one.",
    candidate_states: [makeSession().candidate_states[0]],
    final_result: {
      title: "We could only get this one.",
      formula: "(G (r -> (F b)))",
      explanation: "Whenever red, blue eventually follows.",
      english: "",
      examples_in: [],
      examples_out: [],
      message: "We could only get this one.",
    },
  });

  await installSessionStorage(page, session);
  await installApiMocks(page);

  await page.goto("/");
  await page.locator("#resultStartFreshBtn").click();

  await expect(page.locator("#promptInput")).toHaveValue("");
  await expect(page.locator("#atomsList")).toContainText("No formula yet.");
  await expect(page.locator("#workspaceSection")).toHaveClass(/hidden/);

  const stored = await page.evaluate(() => window.localStorage.getItem("pick-ltl-session"));
  expect(stored).toBeNull();
});
