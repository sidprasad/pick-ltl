const path = require("path");
const { defineConfig, devices } = require("@playwright/test");

const pythonCmd = process.env.PICK_LTL_PYTHON || "python";
const pythonPath = [path.resolve(__dirname, "src"), process.env.PYTHONPATH]
  .filter(Boolean)
  .join(path.delimiter);

module.exports = defineConfig({
  testDir: path.join(__dirname, "tests", "e2e"),
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:4173",
    headless: true,
  },
  webServer: {
    command: `${pythonCmd} -m flask --app pick_ltl.app:app run --port 4173 --no-debugger --no-reload`,
    url: "http://127.0.0.1:4173",
    reuseExistingServer: !process.env.CI,
    env: {
      PYTHONPATH: pythonPath,
    },
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
      },
    },
  ],
});
