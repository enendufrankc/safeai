# SafeAI v0.7.0 Release Notes

Date: 2026-02-20  
Status: Phase 7 release gate passed

## Scope included

1. Intelligence layer with 5 AI advisory agents
- auto-config agent for generating SafeAI configurations from project context
- policy recommender agent for suggesting policies based on use case
- incident explainer agent for human-readable explanations of policy violations
- compliance mapper agent for mapping policies to regulatory frameworks
- integration generator agent for producing framework adapter snippets

2. BYOM backend abstraction
- pluggable backend supporting Ollama and OpenAI-compatible providers
- expanded provider list including Gemini, Mistral, Groq, and DeepSeek
- metadata sanitizer ensuring AI never sees raw protected data

3. Intelligence CLI and endpoints
- `safeai intelligence` CLI with 5 subcommands (one per agent)
- proxy and dashboard intelligence endpoints
- human approval via staging directory workflow
- interactive intelligence setup in `safeai init`

4. Documentation and notebooks
- rewritten OpenClaw example
- coding agents example
- MkDocs site with 55 pages
- 11 interactive notebooks

5. Test coverage
- 94 new tests across 8 test files

## Validation summary

- `ruff check safeai tests` passed.
- `mypy safeai` passed.
- `pytest` passed (`265` tests).

## Packaging note

- Local wheel/sdist build remains blocked in this environment because `python3 -m build` requires module `build`, which is not installed locally.
- CI release should build artifacts in a controlled environment with build dependencies available.
