# emojibench

emojibench is research software for original science mashups and visual
stories. The Offline Kitchen MVP combines two catalog concepts without an API
key or an internet connection.

The first catalog contains eight original SVG illustrations. It includes
cells, laboratory equipment, science themes, a macrophage, and a superhero.
The preview generator is a deterministic mock. It is not a generative model.

## Install the Python package

Install the locked Python environment:

```shell
uv sync --frozen
```

List and validate the bundled concepts:

```shell
uv run --frozen emojibench catalog list
uv run --frozen emojibench catalog validate
```

Create a PNG preview:

```shell
uv run --frozen emojibench combine macrophage superhero --output preview.png
```

The command writes the preview to the selected path. It records the
combination in `.emojibench/combinations.json` in the current directory. Use
an `.svg` output name to create an SVG preview.

## Generate, evaluate, and review

`emojibench generate` runs a generation job for two concepts. The default
provider is `mock`, which works offline and never makes a network call:

```shell
uv run --frozen emojibench generate macrophage superhero
```

The command prints the draft asset id and the image path. Drafts land in
`.emojibench/generated/` with a JSON sidecar holding the provenance:
inputs, creative brief, provider, model, settings, checksum, rights
status, and review state.

Set `EMOJIBENCH_PROVIDER=openai` to use the real OpenAI image provider.
It also needs `OPENAI_API_KEY` in the environment. The provider has a
request timeout and bounded retries. `EMOJIBENCH_MAX_API_CALLS` bounds
how many paid calls one process may make; the default is 2. When the
provider is unset or `mock`, the tool spends no money.

Check one generated image with deterministic evaluation:

```shell
uv run --frozen emojibench evaluate .emojibench/generated/<file> --store .emojibench
```

Evaluation checks the file, image type, dimensions, checksum, and
provenance. It never approves an asset. A human does that:

```shell
uv run --frozen emojibench review list
uv run --frozen emojibench review approve <asset-id> --reviewer "Your Name"
uv run --frozen emojibench review reject <asset-id> --reviewer "Your Name" --reason "..."
```

Approved generated assets join the public catalog view:

```shell
uv run --frozen emojibench catalog list --store .emojibench
```

## Build a story

Compose a three-to-five panel story from approved assets. Write a JSON
file with a title, an audience, and ordered panels:

```shell
uv run --frozen emojibench story create examples/macrophage-saves-the-day.json
```

The command validates the panels, exports the story JSON, and copies each
panel image to `.emojibench/stories/<story-id>/`. Every panel states its
evidence category: observation, interpretation, or creative analogy.
Observation panels need a reference. See
[Single-cell extensions](docs/src/single-cell.md) for how a panel links
to real microscopy metadata without replacing the source image.

## Run the web kitchen

Install the frontend packages:

```shell
cd web
npm install
```

Start the local development server:

```shell
npm run dev
```

Open the local address that Vite prints. Search the catalog. Fill both
selection slots. Then download the SVG preview.

The web build includes the catalog and image files. Without a backend it
makes no calls to an external service.

## Run the API backend (optional)

The FastAPI backend adds provider generation, review, and story export
over HTTP:

```shell
uv run --frozen python -m uvicorn emojibench.api:app --port 8000
```

With the backend running, the web kitchen detects it automatically and
shows the generation controls and the story builder. Endpoints:
`GET /api/assets`, `GET /api/combinations`, `POST /api/generations`,
`GET /api/generations/{id}`, `POST /api/review/{id}/approve`,
`POST /api/review/{id}/reject`, `POST /api/stories`. Generation defaults
to the offline mock provider, so the backend alone makes no paid calls.

## Run the checks

Run the Python test suite from the repository root:

```shell
uv run --frozen pytest
```

Run the frontend checks from `web/`:

```shell
npm run build
npx vitest run
```

## License and artwork

The software and original sample artwork use the BSD 3-Clause license. See
[LICENSE](LICENSE) for the full terms.

The sample assets were drawn for this project. The repository does not copy or
include Emoji Kitchen artwork.
