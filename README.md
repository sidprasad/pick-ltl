# PICK LTL

PICK LTL is a local Python web app for building Linear Temporal Logic formulas with a PICK-style loop:

1. Ask an LLM for one seed formula.
2. Derive alternative candidates locally using misconception and syntactic mutation.
3. Distinguish candidates by classifying traces.
4. Stop when one candidate survives, or when the app can only confidently offer a single seed-derived interpretation.

## Getting Started

If you just want to try the app locally, do these steps in order.

### 1. Create and activate a Conda environment

From pick-ltl:

```bash
conda create -n pick-ltl python=3.12
conda activate pick-ltl
```

Python 3.12 is the recommended default because it works well with current `conda-forge` builds of `spot`.

### 2. Install `spot`

`spot` is required for LTL equivalence checks and trace generation.

```bash
conda install -c conda-forge spot
```

### 3. Install Python dependencies

With `pick-ltl` activated:

```bash
pip install -e ".[dev]"
```

If `conda` is not already available on your machine, install Miniforge or Conda first.

### 4. Start the web app

```bash
./scripts/run.sh
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

### 5. Connect your local model

When the app opens:

1. Click `Settings`.
2. Pick a provider.
3. Enter the provider URL and model name.
4. Click `Test Connection`.
5. Click `Save Settings`.

### 6. Generate your first formula

Once settings are saved:

1. Enter a natural-language description such as `Whenever the red light is on, the blue light eventually turns on`.
2. Click `Generate`.
3. Review the proposed atomic propositions.
4. If multiple candidates were derived, classify the traces shown in the app.
5. If only one candidate was derivable, the app will show `We could only get this one.`

## Requirements

- Python 3.10+
- `spot`

## Provider Presets

- `Ollama`
- `OpenAI-compatible`

Configure the provider in the app’s settings panel. Settings are saved to `~/.config/pick-ltl/settings.json` unless `PICK_LTL_CONFIG_DIR` is set.

## Using A Local Llama Model

If your local Llama model is running through `Ollama`, use:

- Provider: `Ollama`
- Base URL: `http://localhost:11434`
- Model: the exact model name reported by Ollama, for example `llama3.2:latest`

You can confirm the model name with:

```bash
ollama list
```

If your local Llama model is running behind an OpenAI-compatible server instead, use:

- Provider: `OpenAI-compatible`
- Base URL: your server base URL, commonly something like `http://localhost:8000/v1`
- Model: whatever model ID that server exposes

## Typical First Run

For the simplest local path with Ollama:

1. Create the environment: `conda create -n pick-ltl python=3.12`
2. Activate it: `conda activate pick-ltl`
3. Install Spot: `conda install -c conda-forge spot`
4. Install the repo: `pip install -e ".[dev]"`
5. Start Ollama and make sure your model is available.
6. Run `./scripts/run.sh`.
7. Open the app in the browser.
8. Open `Settings`.
9. Set provider to `Ollama`.
10. Leave the base URL as `http://localhost:11434` unless your Ollama server is elsewhere.
11. Enter your model name.
12. Click `Test Connection`.
13. Click `Save Settings`.
14. Enter a prompt and click `Generate`.

## Troubleshooting

### The app will not start

- Make sure you activated the Conda environment with `conda activate pick-ltl`.
- Make sure `pip install -e ".[dev]"` completed successfully.
- Make sure `spot` is installed in the environment you are using.

### The model connection fails

- If using Ollama, make sure the Ollama server is running.
- Check that the base URL is correct.
- Check that the model name exactly matches what the server exposes.

### I get formula-generation errors immediately

- The provider may be returning non-JSON output or an unexpected response shape.
- Try a different local model if the current one does not follow structured output reliably.
- If you are using a local OpenAI-compatible server, confirm it supports chat-completions style requests.

## Notes

- Session state lives in the browser and can be exported/imported as JSON.
- The app does not require a database.
- If mutation cannot produce a meaningful candidate set, the UI falls back to “We could only get this one.”
