
name will be emojibench for the project
We'll use emojibench as the project name going forward, replacing single-storyceller in the specification.

Updated naming:

Project/repository: emojibench

Python package: emojibench

CLI: emojibench

Web application: EmojiBench

Tagline: A creative laboratory for visual storytelling.

Scope: Agent-powered emoji mashups, scientific illustrations, and single-cell storytelling.

We'll retain the CU-DBMI Python research software template as the foundation and Emoji Kitchen as the interface inspiration.

The name also leaves room for a future benchmarking component that evaluates generated illustrations for quality, consistency, and scientific accuracy.

description for github repo?
Agent-powered emoji mashups and visual storytelling for single-cell science.

best agent on claude or codex which can do this from hermes?
For building EmojiBench from Hermes Agent, I'd choose Codex as the primary coding agent, with Claude Code as an optional second agent for architecture and code review.

Hermes already supports both through dedicated coding-agent skills. 

Hermes Agent
+1

Codex

Claude Code

Best use

Implementing features and tests

Complex architecture and refactoring

Autonomous work

Excellent for scoped tasks

Strong for longer development sessions

Hermes integration

Built-in skill

Built-in skill

My choice for EmojiBench

Primary

Optional reviewer

For your project, I'd use this workflow:

Hermes acts as the coordinator and reads the EmojiBench specification.

Codex creates the repository from your CU-DBMI template and implements features in small, testable steps.

Claude Code optionally reviews larger architectural changes.

Hermes checks test results and prepares the next task.

Getting started
Inside Hermes, use its existing codex skill. The official skill catalog also includes claude-code. 

Hermes Agent

To choose a Codex-backed model directly in Hermes:

hermes model

Select ChatGPT or Codex Subscription. Hermes supports that authentication path, although usage eligibility depends on your subscription. 

Hermes Agent

Initial instruction for Hermes
Copy into Hermes

Build EmojiBench using https://github.com/CU-DBMI/template-uv-python-research-software as the foundation and https://github.com/xsalazar/emoji-kitchen as the interface reference.

Delegate implementation to Codex. Preserve the Python template's testing, CI, and agent skills.

Start with a working two-emoji combination interface, then add image generation, evaluation, and single-cell storytelling.

Implement incrementally, run tests after each change, and create reviewable commits. Verify upstream licensing before reusing code or artwork.

One distinction: Hermes can either use a Codex model directly or delegate development to the actual Codex CLI. For building a repository, I'd prefer delegation to the Codex CLI, because it provides the specialized coding workflow, rather than only using the model through Hermes.

full markdown instructions?

Worked for 16s

I've created the full Markdown implementation instructions for Hermes to build EmojiBench using Codex.

emojibench-hermes-instructions.md

Complete implementation brief, ready to give to Hermes

The instructions cover repository setup using your CU-DBMI template, the Emoji Kitchen-inspired React interface, agent-driven image generation, quality evaluation, and single-cell storytelling.

They also include:

Five implementation milestones with acceptance criteria.

Instructions for Hermes to delegate coding work to Codex.

Python package, CLI, API, and frontend architecture.

Testing, CI, agent skills, and scientific provenance requirements.

Licensing safeguards and an offline demo that works without paid AI APIs.

I verified that Hermes provides a bundled Codex delegation skill, including instructions for invoking the Codex CLI. 

GitHub

To start: Give Hermes the Markdown file and ask:

Follow these instructions to build EmojiBench. Start with Milestone 0, use Codex for implementation, and validate each milestone before continuing.

EmojiBench — Hermes Implementation Instructions
Project: emojibench
Python package: emojibench
CLI: emojibench
Working description: Agent-powered emoji mashups and visual storytelling for single-cell science.

Your role
You are Hermes, the coordinating agent for building EmojiBench. Delegate scoped coding tasks to the Codex CLI using Hermes's bundled autonomous-ai-agents/codex skill. Remain responsible for planning, checking results, running acceptance checks, and reporting progress. Claude Code may serve as an optional independent reviewer; it is not required.

Do actual repository work rather than producing only a plan. Complete each milestone in small, independently testable changes. Do not claim success unless the tests or interface were actually run.

Source repositories
Research-software foundation: https://github.com/CU-DBMI/template-uv-python-research-software
Interaction reference: https://github.com/xsalazar/emoji-kitchen
Related catalog/backend reference: https://github.com/xsalazar/emoji-kitchen-backend
Read the repositories and their current documentation before changing code. Prefer the current checked-out files over assumptions in this brief.

Important licensing requirement: The Emoji Kitchen frontend did not expose a root LICENSE file when this plan was prepared. Do not copy its source or Google's sticker assets into EmojiBench without verifying permission. Reimplement the useful interaction patterns independently unless rights are established. Do not download or redistribute an unlicensed sticker catalog as part of the deliverable.

Product goal
Build an open-source, Python-first application for combining visual concepts and turning them into illustrations and short stories.

The first version should support:

A searchable catalog of original or appropriately licensed concepts/assets.
A two-item selection interface inspired by Emoji Kitchen.
A generated image or existing approved mashup for a selected pair.
Saving, evaluating, reviewing, and downloading generated assets.
A simple illustrated story assembled from approved assets.
A path for connecting real single-cell microscopy images and metadata later.
Make fun mashups work first. Do not let the future research features delay a functioning vertical slice.

Engineering foundation
Bootstrap from the CU-DBMI Copier template, selecting pure Python (use_rust=false). The template already includes uv, pytest, coverage, pre-commit, Ruff, ty, GitHub Actions, a CLI, docs, and .agents/skills/. Retain these conventions rather than replacing them.

Suggested initial command, after confirming Copier options:

uvx copier copy --vcs-ref=HEAD \
  https://github.com/CU-DBMI/template-uv-python-research-software \
  emojibench
Supply project-specific Copier answers: project_name=emojibench, a short description, appropriate author/citation metadata, actual repository URL, and use_rust=false. Do not invent author names, ORCIDs, or repository ownership. If the destination is already a repository with files, inspect it first and apply the template without destroying existing work. Initialize git if needed; Codex CLI requires a git repository.

Use the template's own validation commands where available, including:

uv sync
uv run --frozen pytest
uv run --frozen poe pipeline
pre-commit run --all-files
Do not assume poe pipeline can run before dependencies and the template are set up. Fix any generated-template issues before adding features.

Recommended architecture
One repository, two clear layers:

Python package for models, catalog, generation providers, evaluation, story composition, metadata, CLI, and optional FastAPI backend.
React + TypeScript + Vite frontend under web/, with a two-selector visual kitchen.
Use JSON files for an initial read-only asset catalog and local files for generated images. If generation/review workflows need concurrent writes and status transitions, introduce SQLite. Do not start with a distributed database, message broker, or cloud deployment.

Proposed layout (adapt it to the generated template):

emojibench/
├── AGENTS.md
├── .agents/skills/
│   ├── ...existing template skills...
│   ├── visual-generation/SKILL.md
│   ├── scientific-review/SKILL.md
│   └── story-construction/SKILL.md
├── src/emojibench/
│   ├── __init__.py
│   ├── cli.py
│   ├── models.py
│   ├── catalog.py
│   ├── combinations.py
│   ├── generation.py
│   ├── evaluation.py
│   ├── stories.py
│   ├── providers/
│   └── api/
├── tests/
├── web/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── api/
│   └── package.json
├── examples/
├── docs/
├── pyproject.toml
└── README.md
Keep components narrowly scoped and easy to test.

Product specification
1. Visual Kitchen
The default screen lets a user select two concepts such as macrophage + superhero. Offer search, selection, a combined preview, a generate action when needed, and a PNG download.

The catalog should distinguish:

Existing, approved combination
No existing combination; generation available
Generation queued/running
Generated draft needing review
Rejected or unavailable combination
A local demo must work without paid AI access. Supply a handful of original SVG/PNG sample assets or safe programmatically drawn illustrations, and a deterministic mock provider. Do not imply that the mock output is a real generative model.

2. Generation
Implement a replaceable ImageProvider abstraction, with:

A no-network mock provider for tests and local demos.
An optional real image-generation provider, configured by environment variables.
Input validation, timeouts, bounded retries, and user-facing error messages.
Explicit per-job cost or call limits when a paid provider is enabled.
The output is an asset plus metadata: inputs, creative brief, model/provider, generation timestamp, prompt/settings where shareable, output checksum, rights status, and review state.

Never commit API credentials. Do not automatically spend money on an unconfigured provider.

3. Evaluation and review
Use deterministic checks first:

File exists and decodes
Allowed image type
Expected dimensions
Transparency where required
Content checksum
Required metadata
Duplicate or near-duplicate warning where feasible
Optionally allow a vision model to suggest scores for quality, recognizability, style, and adherence to the brief. Treat model assessments as suggestions, not ground truth. The MVP requires human approval before publication. Ensure drafts cannot enter the approved public catalog through API or CLI shortcuts.

4. Story Kitchen
Let users arrange three to five visual panels, enter or generate captions, choose an audience level, preview, and export their story as images and JSON.

First demonstration: “A Macrophage Saves the Day” using approved illustrations. Keep biology explanations accurate and age-appropriate; do not assert that a whimsical superhero illustration is scientific evidence.

5. Single-cell extensions
Design models so a future asset can reference:

A source microscopy image, image crop, or object
Image dimensions and coordinate/crop metadata
Optional segmentation/object identifier
Optional measurements/features
Source dataset, attribution, and license
Associated scientific references
Do not implement segmentation, Zarr, AnnData, CytoDataFrame, or OME-Arrow integrations in the first milestone unless a simple prototype is already possible. Leave documented extension points and one illustrative fixture. Preserve experimental images independently of stylized renderings.

Data contracts
Use Pydantic or equivalent typed models for:

Asset

id, name, category, tags, image_uri
source, license, kind (original, generated, scientific)
status (draft, approved, rejected)
generation_metadata (optional)
scientific_metadata (optional)
Combination

id, ordered or normalized input_ids (document whether order matters)
output_asset_id (optional)
status, created_at, evaluation (optional)
Story

id, title, audience, ordered panels
Each panel: asset_id, caption, optional references, evidence_status
status, created_at
Define versioned JSON schemas. Ensure stable IDs, consistent serialization, sensible error messages, and migration paths when schemas evolve.

APIs and commands
Expose core behaviors from Python first. Suggested CLI, to implement incrementally:

emojibench catalog validate
emojibench catalog list
emojibench combine macrophage superhero
emojibench evaluate path/to/image.png
emojibench story create path/to/story.json
For the web application, add a thin FastAPI layer only when needed:

GET  /api/assets
GET  /api/combinations?first=...&second=...
POST /api/generations
GET  /api/generations/{id}
POST /api/stories
GET  /api/stories/{id}
Avoid holding a request open indefinitely for image generation. Provide a job/status abstraction; in local development a bounded in-process worker is acceptable. Do not present it as durable distributed infrastructure.

Agent instructions
Hermes must read the repository's AGENTS.md and load relevant project skills before instructing Codex. Preserve the template's test-driven, incremental implementation, code review, CI, and plain-English guidance.

Create project skills:

visual-generation: coherent prompts, output styles, asset licensing and metadata.
scientific-review: distinguish observation, interpretation, and creative analogy; require sources for claims.
story-construction: short panels, narrative continuity, audience-appropriate captions, and traceable references.
Use skills for decisions and judgment. Use Python code for deterministic data validation and state transitions.

Delegation protocol
Check that Codex CLI is installed and authenticated. The bundled Hermes codex skill documents prerequisites and interactive terminal usage. Ask for authentication only when needed.
Read and follow autonomous-ai-agents/codex. Use its preferred terminal/PTY invocation rather than inventing a Hermes-specific command.
Give Codex one bounded task at a time, including files in scope, required tests, and acceptance criteria.
Ask Codex to use a feature branch or isolated worktree when appropriate.
After Codex finishes, review the actual diff, run relevant checks, and resolve failures.
Commit completed changes with descriptive messages; do not push, create remote repos, merge, deploy, or open PRs without explicit permission.
If a task repeatedly fails, narrow it and report the concrete blocker. Never claim unrun tests passed.
Example delegation request to Codex:

Implement the versioned Asset and Combination Pydantic models and a JSON catalog loader in src/emojibench/. Include schema tests, malformed-file tests, sample fixture data, and documentation. Follow AGENTS.md. Do not change the frontend. Run the relevant pytest suite and summarize the files changed, tests run, and unresolved issues.

Claude Code may be used for an optional independent review after a milestone. Do not require both coding agents for routine changes.

Milestones and acceptance tests
Milestone 0 — Inspect and scaffold
Inspect repository contents and upstream documentation.
Verify licenses before copying any code or assets.
Scaffold from the Python template.
Configure emojibench metadata, package, tests, and README.
Establish local validation commands.
Confirm a clean test run.
Done when: A contributor can clone the repository, uv sync, and run template tests.

Milestone 1 — Offline kitchen MVP
Add Asset and Combination models.
Create a small catalog of licensed/original sample concepts.
Implement selection/lookup and a deterministic combination mock.
Build the React/Vite two-selector UI.
Preview and download a sample result.
Add frontend tests or suitable interaction tests.
Done when: With no credentials or network model calls, a user can choose two concepts, preview a result, and download it.

Milestone 2 — Real generation and review
Add one configurable image provider.
Add jobs and error states.
Store results and provenance.
Add deterministic validation and optional AI evaluation.
Require approval before public publication.
Guard against runaway API costs.
Done when: A configured provider can generate a draft, which can be reviewed and approved, while an unconfigured installation still works offline.

Milestone 3 — Story Kitchen
Compose three-to-five-panel stories from approved assets.
Edit captions and choose audience level.
Export story JSON and panel images.
Provide one scientifically reviewed example.
Add validation tests for references and panel order.
Done when: The demo produces a shareable, reviewable story with provenance.

Milestone 4 — Science-ready metadata
Add optional microscopy source references and crop/object metadata.
Provide one small licensed scientific fixture or metadata-only example.
Document future integrations with OME-Arrow, CytoDataFrame, and related formats.
Verify scientific observations and generated art remain distinguishable.
Done when: A story panel can link to original scientific evidence without replacing or modifying it.

Testing and release gates
For each milestone:

Unit tests for models, validation, and status transitions
Integration tests for API and catalog
Offline/mock generation tests in CI
Frontend build plus a minimal user-flow test
Type and lint checks consistent with the template
Failure-path tests (invalid asset, provider unavailable, rejected draft)
Docs and sample commands verified against actual behavior
Do not add hardcoded secrets, unlicensed art, or expensive provider calls to CI.

Initial prioritized task list
Audit the current working repository and both upstream references.
Scaffold the Python project from the CU-DBMI template.
Implement Asset/Combination models with tests.
Create five to ten original demo assets and metadata.
Build the two-selector kitchen frontend.
Connect the frontend to a mock combination provider.
Implement PNG download.
Add generation-provider interface and a configurable real provider.
Add review state, deterministic evaluation, and approvals.
Add three-panel story composition and export.
Document scientific provenance and future microscopy integrations.
Scope control
Do not initially implement:

Custom foundation model training
Multi-agent swarms
Kubernetes or queue infrastructure
Authentication for many users
Huge metadata warehouses
Automatic scraping of Google assets
Automatic scientific truth claims
Video/animation rendering
Full single-cell segmentation and feature extraction
Favor working software over elaborate abstractions. Maintain compatibility with the baseline template.

Reporting expectations
At the end of each milestone, report:

What is working.
What files changed.
Exact tests/commands run and their results.
How to launch and inspect the demo.
Known limitations and licensing concerns.
The next bounded implementation task.
Start now with Milestone 0. If an emojibench repository already exists, inspect and preserve its contents. Only ask questions that block safe implementation; otherwise choose reasonable defaults and document them.






