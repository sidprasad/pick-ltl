# PICK LTL

PICK LTL is a local Python web app for building Linear Temporal Logic formulas with a PICK-style loop:

1. Ask an LLM for one seed formula.
2. Derive alternative candidates locally using misconception and syntactic mutation.
3. Distinguish candidates by classifying traces.
4. Stop when one candidate survives, or when the app can only confidently offer a single seed-derived interpretation.

## Getting Started

If you just want to try the app locally, do these steps in order.

### 1. Install Python dependencies

From pick-ltl:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Install `spot`

`spot` is required for LTL equivalence checks and trace generation. It is not installed from PyPI here.

```bash
conda install -c conda-forge spot
```

If `conda` is not already available on your machine, install Miniforge or Conda first.

### 3. Start the web app

```bash
./scripts/run.sh
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

### 4. Connect your local model

When the app opens:

1. Click `Settings`.
2. Pick a provider.
3. Enter the provider URL and model name.
4. Click `Test Connection`.
5. Click `Save Settings`.

### 5. Generate your first formula

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

1. Start Ollama and make sure your model is available.
2. Run `./scripts/run.sh`.
3. Open the app in the browser.
4. Open `Settings`.
5. Set provider to `Ollama`.
6. Leave the base URL as `http://localhost:11434` unless your Ollama server is elsewhere.
7. Enter your model name.
8. Click `Test Connection`.
9. Click `Save Settings`.
10. Enter a prompt and click `Generate`.

## Troubleshooting

### The app will not start

- Make sure you activated the virtual environment with `source .venv/bin/activate`.
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
