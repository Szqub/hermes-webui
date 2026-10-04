## Thinking Path

A pick on the configured Custom endpoint was encoded as `@custom:<model>`. A
pick on a named custom record is encoded as `@custom:<slug>:<model>`. Both live
in the same `@provider:model` namespace, and the parser can only split the
string, so the two cases are indistinguishable whenever the identifier itself
contains a colon — normal for Ollama tags (`qwen3:8b`) and for vLLM or
llama.cpp revisions.

The failure is not cosmetic. With `model.provider: ollama` and a `base_url`, the
picker aliases the active provider to `custom`; a Custom pick of `qwen3.8:27b`
is re-read as "named provider `custom:qwen3.8`, model `27b`". The request leaves
the configured endpoint for that record's `base_url`, presents that record's
credentials, and asks for a truncated id. Two independent decisions — which
endpoint, and which identifier — collapse into one ambiguous string, and the
wrong one wins.

Every repair that keeps using `@custom:` inherits the ambiguity, so the
configured lane needs its own wire form, provably unreachable from the generic
encoder rather than merely unlikely.

## What Changed

Configured Custom selections use a reserved route:

- `@!:M` — the configured endpoint lane. Everything after the first three
  characters is the opaque identifier M, slashes and colons included.
- `@E(P):M` — the generic provider route, unchanged in shape, but the provider
  segment is escaped when it is not legacy-safe: `!` and `%` are always
  percent-encoded, so no provider id can emit the reserved prefix.

Disjointness is by construction. The generic encoder
(`_encode_provider_qualified_model_id` in `api/config.py`, `_encodeModelRoute`
in `static/ui.js`) preserves only `[a-z0-9_.~-]+`, `custom:<slug>` and
`custom:<host>:<port>`; everything else is escaped. A provider literally named
`!`, `!:payload` or `%21` encodes as `@%21:...`, `@%21%3Apayload:...` and
`@%2521:...`. The reserved branch is tested before any percent decoding.

Resolution order in `resolve_model_provider`:

1. `@!:` is consumed first — before configured-provider alias resolution, before
   ownership scans, before the generic parser — and returns the whole suffix,
   provider `custom`, and `model.base_url`. `providers.ollama`, `providers.local`
   and any named record are not consulted. Missing endpoint, empty suffix, or an
   active named `custom:slug` fails closed.
2. Everything else keeps today's behavior: named custom records, explicit
   `@local:` / `@ollama:`, endpoint-derived `custom:host:port`,
   `providers.custom-configured`, slash-id routing, and the #4728 fail-closed
   rule for a missing named slug.

The catalog cooperates instead of relying on precedence.
`_encode_catalog_route` emits `@!:M` for an option belonging to the configured
lane, so the Custom group never advertises the ambiguous `@custom:M` spelling;
every other provider, and any configuration without that endpoint, keeps the
generic escaped route.

**The option's own lane decides how a value is read.** `_parseModelRoute`
consults the caller's hint before the legacy `@custom:` split. The catalog sets
an option's `data-provider` to the group it listed the model under, so a plain
Custom-lane option is `@custom:<model>` in group `custom` and the whole
remainder is the model id. Splitting there first read a colon-bearing id as a
record name and truncated it:

    @custom:qwen3:8b          before -> {"model":"8b","model_provider":"custom:qwen3"}
                              after  -> {"model":"qwen3:8b","model_provider":"custom"}
    @custom:vendor/qwen3:8b   before -> {"model":"8b","model_provider":"custom:vendor/qwen3"}
                              after  -> {"model":"vendor/qwen3:8b","model_provider":"custom"}

`_deduplicateModelPickerOptions` shares the parser, so it dropped distinct
models as a side effect: identities `['8b','8b','7b','9b']` removed one option
from the group; they are now `['qwen3:8b','llama3.1:8b','qwen2.5.coder:7b','gemma2:9b']`
and nothing is removed. A value read under a named record
(`@custom:backup:model-a` with hint `custom:backup`) still resolves to that
record and model `model-a`.

## Why It Matters

- A selection on the configured endpoint always reaches that endpoint, with the
  whole identifier and that endpoint's credentials, no matter what the catalog
  or `providers.*` contains.
- No named record can be hijacked by a colon-bearing identifier, and no named
  record can hijack the configured lane.
- The two decisions are separated structurally, so this class of bug cannot come
  back through a new spelling of `@custom:`.
- The browser no longer truncates an identifier it just rendered, and the picker
  no longer deletes distinct models from the Custom group.
- Old sessions are not silently re-routed: a stored `@custom:qwen3:8b` still
  means what the parser has always said it means, in both languages, and the
  reserved form is only written when the configured entry is selected again.

## Verification

Reported shape (the issue's own configuration — `model.provider: ollama` with
`base_url: http://127.0.0.1:11434/v1`, identifier `qwen3.8:27b`), through the
real encoder and resolver:

    reserved lane: True
    session ('qwen3.8:27b', 'custom') -> wire '@!:qwen3.8:27b'
                                      -> ('qwen3.8:27b', 'custom', 'http://127.0.0.1:11434/v1')

- Acceptance matrix through the real encoder and resolver on both commits: 68
  rows, 61 changed, every overlap row now returning
  `(whole identifier, custom, configured base_url)`; on the base those rows
  return `(truncated id, custom:qwen3, null)` or
  `(truncated id, custom:qwen3, <named base_url>)`. Run for `ollama`, `vllm`,
  `lmstudio`, `llamacpp`, `local`, against `custom_providers: [{name: lab}]` and
  `providers: {lab: ...}`, with and without a competing
  `providers.ollama.base_url`.
- Targeted suite: `tests/test_issue7955_disjoint_route.py`,
  `tests/test_issue7955_route_js.py`, `tests/test_issue854_live_model_prefix.py`,
  `tests/test_model_picker_badges.py` — **101 passed**.
- Those tests fail on the base `cdff0b8d`: **79 failed, 12 passed**; the base
  source contains zero occurrences of `@!:`.
- Full suite on this branch: **18007 passed, 3 failed, 236 skipped, 2 xfailed,
  2 xpassed, 399 subtests passed** in 966s. The three failures are
  environment-dependent and fail identically on the base `cdff0b8d`:
  `test_managed_profile_startup::test_real_managed_bootstrap_preserves_named_profile_concurrency`
  and the two `test_tls_aware_probe` cases (the health probe needs a live
  server). A full run on the pre-fix state of this branch reported six, the
  extra three (`test_minimax_provider` x2 and
  `test_profile_switch_models_disk_cache[plugin-version-bumped]`) pass in
  isolation on both trees and are flaky under the full parallel run.
- Adversarial encoder inputs through the real catalog producer: `custom`,
  `custom:a:b`, `Custom:Lab`, `+x`, `%2Bx`, `foo bar`, `foo:bar:baz`, empty,
  whitespace-only, surrounding whitespace, non-string, a 10,000-character id,
  `!`, `!:payload`, `a!b`, `@!:` and percent-bearing host-like ids. No input
  reaches the reserved prefix; Python and JavaScript agree on every one.
- `node --check` on the touched scripts and `git diff --check` are clean.
- No live upstream completion and no visual browser session: the JavaScript
  checks execute the real picker functions against small DOM substitutes.
  Routing and selection logic is covered; layout is not touched.

## Risks / Follow-ups

- **Known gap, not fixed here and pre-existing on the base.** When the active
  provider is a cloud provider (`anthropic`, `openrouter`) or `lmstudio` without
  `model.base_url`, and an *unnamed* `custom_providers` entry supplies the
  endpoint, the Custom group is advertised as `@custom:<model>` and the route is
  unresolvable — `resolve_model_provider('@custom:qwen3:8b')` returns
  `('8b','custom:qwen3', None)`. The reserved predicate requires
  `model.base_url`, while the endpoint lives in that entry. Closing it means
  letting the catalog predicate and the resolver guard agree that an unnamed
  `custom_providers` entry is the configured Custom endpoint. That touches the
  resolver, so it is deliberately out of scope for this PR and should be filed
  separately. This PR neither causes nor worsens it; it does stop the picker
  from truncating the identifier in that configuration.
- A session stored before this change with a colon-bearing identifier on the
  configured lane keeps its historical resolution (the named record) until the
  entry is selected again. Repairing it automatically needs provenance the
  stored string does not carry. Documented in
  `docs/architecture/configured-custom-routing.md`.
- A historic provider name containing a literal `!` or a percent escape cannot
  be told apart from the newly escaped form. Re-selection re-emits it escaped;
  downgrade cannot read the reserved form.
- The reserved token follows the active `model.base_url`, not a snapshot from
  session creation. Changing or removing the endpoint changes authority, and a
  missing endpoint fails closed rather than borrowing another record.
- Docs updated: `docs/architecture/configured-custom-routing.md` (new) and
  `docs/CONTRACTS.md` (index link). Release-note wording: "Configured Custom
  model selections now use a dedicated wire route, so colon-bearing model ids
  (`qwen3:8b`) stay on the configured endpoint with the full identifier."

## Contract Routing

- Task type: routing bug fix (#7955).
- Touched areas: session selection wire representation, configured endpoint
  authority, catalog prefix emission, browser picker identity, dedup and
  persistence.
- Relevant public docs: `CONTRIBUTING.md`, `docs/CONTRACTS.md`,
  `docs/architecture/configured-custom-routing.md`.
- Scope boundaries: no upstream protocol, credential store, session schema or UI
  layout change.

## Contract Change

- Previous: the configured Custom lane and named custom records shared the
  `@custom:` syntax, so a colon-bearing identifier could change endpoint
  ownership and be truncated.
- New: the configured lane is `@!:M` with an opaque suffix; the generic provider
  encoder escapes `!` and `%` so it cannot produce that prefix; resolution
  consumes the reserved branch before ownership scans and generic parsing; and
  the picker reads a value through the lane the option was listed under.
- Compatibility: named selections keep their meaning, ambiguous persisted values
  are never rewritten by parsing, and re-selecting the configured entry writes
  the unambiguous form. Historic `!`/percent provider spellings and the
  downgrade limit are documented.

## Model Used

[NEEDS SZQUB'S DECISION — see the note sent with this draft. The repository
checklist asks for a disclosure here; the standing rule is that only Szqub is
the author and signatory. Nothing has been written into this section.]