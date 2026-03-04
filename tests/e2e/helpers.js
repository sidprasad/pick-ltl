function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

const provider = {
  kind: "ollama",
  base_url: "http://localhost:11434",
  model: "mock-llm",
  api_key: "",
  timeout_seconds: 60,
};

const atoms = [
  { name: "r", meaning: "red light is on" },
  { name: "b", meaning: "blue light is on" },
];

function makeSeed(formula, explanation, warnings = []) {
  return {
    formula,
    explanation,
    atoms: clone(atoms),
    warnings: [...warnings],
  };
}

function makeCandidate(formula, explanation, originKind = "seed") {
  return {
    formula,
    explanation,
    origin: {
      kind: originKind,
      misconception_code: null,
    },
    confidence: null,
    equivalents: [],
    positive_votes: 0,
    negative_votes: 0,
    elimination_threshold: 2,
    eliminated: false,
  };
}

function makeSession(overrides = {}) {
  const seedA = makeSeed("(G (r -> (F b)))", "Whenever red, blue eventually follows.");
  const seedB = makeSeed("(F r)", "Eventually red happens.");

  return {
    version: 1,
    prompt: "Whenever the red light is on, the blue light eventually turns on.",
    provider: clone(provider),
    seed: clone(seedA),
    seeds: [clone(seedA), clone(seedB)],
    candidate_states: [
      makeCandidate(seedA.formula, seedA.explanation, "seed"),
      makeCandidate(seedB.formula, seedB.explanation, "seed"),
    ],
    history: [],
    mode: "voting",
    warnings: [],
    current_pair: null,
    final_result: null,
    exhausted: false,
    message: "",
    ...clone(overrides),
  };
}

function withPair(session, trace1, trace2, matches1, matches2) {
  const next = clone(session);
  next.current_pair = {
    trace1,
    trace2,
    matches1: matches1 || [],
    matches2: matches2 || [],
  };
  return next;
}

function installSessionStorage(page, session) {
  return page.addInitScript((storedSession) => {
    window.localStorage.setItem("pick-ltl-session", JSON.stringify(storedSession));
  }, session);
}

async function installApiMocks(page, handlers = {}) {
  const defaultHandlers = {
    "GET /api/settings": clone(provider),
    "POST /api/models": { models: ["mock-llm"] },
    "GET /api/models": { models: ["mock-llm"] },
  };

  const state = new Map();
  for (const [key, value] of Object.entries({ ...defaultHandlers, ...handlers })) {
    state.set(key, Array.isArray(value) ? [...value] : value);
  }

  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const key = `${request.method()} ${url.pathname}`;
    if (!state.has(key)) {
      throw new Error(`Unhandled API request in Playwright test: ${key}`);
    }

    const entry = state.get(key);
    const body = request.postData() ? request.postDataJSON() : undefined;

    let response;
    if (Array.isArray(entry)) {
      if (!entry.length) {
        throw new Error(`No mocked responses left for ${key}`);
      }
      const next = entry.shift();
      response = typeof next === "function" ? await next({ body, request }) : next;
    } else {
      response = typeof entry === "function" ? await entry({ body, request }) : entry;
    }

    const status =
      response && typeof response === "object" && Object.prototype.hasOwnProperty.call(response, "status")
        ? response.status
        : 200;
    const payload =
      response && typeof response === "object" && Object.prototype.hasOwnProperty.call(response, "body")
        ? response.body
        : response;

    await route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(payload ?? {}),
    });
  });
}

module.exports = {
  installApiMocks,
  installSessionStorage,
  makeSeed,
  makeSession,
  withPair,
};
