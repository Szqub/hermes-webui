# Custom-lane endpoint authority

Current contract for what the plain `custom` lane means to
`resolve_model_provider()` in `api/config.py`, and why the model id's own
colons are never provider syntax there. Start here before changing
`model_with_provider_context()`, the `@<provider_id>:<model>` hint parser, or
the `custom_providers[]` / `providers:` ownership scans (#7955).

## The round-trip

A model pick travels to the Agent runtime as one string in the session's
`model` field:

1. the picker collapses the session provider to the plain `custom` lane when
   the pick is served by the configured endpoint (`model.base_url`) —
   `model.provider: ollama`, `vllm`, or the legacy `local` spelling;
2. `model_with_provider_context()` encodes the pick;
3. `resolve_model_provider()` turns it back into
   `(model, provider, base_url)`.

The generic encoding is `@<provider_id>:<model>` and the generic parser splits
it on the last `:`. A local-server model id may itself carry a colon — Ollama
and vLLM tags such as `qwen3.8:27b` — so `@custom:qwen3.8:27b` was read back as
provider `custom:qwen3.8` and model `27b`, and the runtime failed with
`custom:qwen3.8 not configured`. That is #7955.

## The contract

When the configured lane **is** the custom endpoint, the plain Custom lane is
endpoint-authoritative: the whole payload after `@custom:` is the model id,
resolved to provider `custom` and the configured `model.base_url`.

- The lane is the custom endpoint when `model.base_url` is set and the raw
  `model.provider` spelling is empty, `custom`, the legacy `local` (treated as
  `custom`), or a local-server provider (`_is_local_server_provider`).
- The payload is taken whole. No `custom_providers[]` ownership scan, no
  `_get_provider_base_url()`, so a same-named `providers:` record — for example
  `providers.ollama.base_url` while `model.provider` is `ollama` — is never
  consulted for a pick the Custom lane made.
- Endpoint and credential authority have one owner: provider `custom` around
  `model.base_url`, which needs no key. A `custom_providers[]` entry named
  `local` does not lend its endpoint or its key to a bare `custom` pick.

## Disjointness from the generic namespace

Provider ids come from user configuration, so *any* name-shaped sentinel can
collide with one. This lane is therefore keyed on typed config membership, not
on spelling, and it fires only when no configured record owns the token:

1. It only fires for a hint that is exactly `custom` or starts with `custom:`,
   so `@custom-configured:<model>` — the collision that sank the earlier
   internal-route idea — cannot enter it.
2. It tests the **token**, not the parsed hint. `_parse_provider_qualified_model_id()`
   shortens `custom:<a>:<b>` to provider `custom:<a>` while it splits, so a
   membership check made on the hint would miss a record keyed `custom:a:b`.
   The lane yields when any `providers:` key names the token as a prefix, so
   such a record keeps its route.
3. It yields when a `custom_providers[]` slug names the token as a prefix,
   preserving the named passthrough and its fail-closed collision behaviour.
4. It yields for endpoint-derived `custom:<host>:<port>` slugs, which keep
   their existing branch.
5. The bare `custom` name is the lane's own, not a route that owns a token: a
   `providers: {custom: …}` record neither grants nor removes the lane, exactly
   as before this change.
6. It reads the **raw** `model.provider` spelling, not the named-slug-resolved
   id: when the active provider is itself a named `custom:<slug>`, an
   unknown-slug token is an explicit named-provider reference and keeps failing
   closed with `base_url=None` (the #4728 rule).

No new token is minted: the `@custom:<model>` wire shape, the encoder, and the
WebUI JavaScript are untouched, so nothing the picker or the catalog can emit
gains a sentinel. What does change is the resolution of tokens that previously
misresolved or errored — including the known ambiguity recorded below.

## Evaluation order in `resolve_model_provider()`

| # | Branch | Fires when |
|---|---|---|
| 1 | endpoint-slug | hint is `custom:<host>:<port>` derived from the configured endpoint |
| 2 | **plain Custom lane (this contract)** | lane is the custom endpoint and the hint is `custom` or non-`host:port` `custom:<rest>` |
| 3 | named custom provider | slug matches a unique `custom_providers[]` entry |
| 4 | generic `@provider:model` | everything else |

## Acceptance matrix

Layout: `model.provider: ollama` with `model.base_url: http://127.0.0.1:11434/v1`,
session provider `custom`, and a competing provider that lists the same ids
(`custom_providers: [{name: lab, base_url: http://10.0.0.8:8000/v1, models:
[mistral-7b, qwen3.8:27b]}]`, or the same records under `providers:`).

| model | before | after |
|---|---|---|
| `mistral-7b` (untagged, offered by both) | `custom`, `base_url=None` | `custom`, `:11434` |
| `qwen3.8:27b` (tagged, offered by both) | `('27b', 'custom:qwen3.8', None)` | `('qwen3.8:27b', 'custom', ':11434')` |
| `llama3` (only on the Ollama lane) | `ollama`, `:11434` | unchanged |
| any of the above, with `providers.ollama.base_url: other:9999` | `custom`, `base_url=None` | `custom`, `:11434` — `other:9999` is never consulted |
| legacy `provider: local` with `providers.local.base_url: other:9999` | `custom`, `base_url=None` | `custom`, `:11434` |
| `custom_providers[name=local]` with its own endpoint and key | `custom`, `base_url=None` | `custom`, `:11434`, no borrowed key |

Holds for both competitor shapes (`custom_providers[]` and `providers:`) and
for the `ollama`, `vllm`, and legacy `local` spellings.

## Deliberately unchanged

- Named `custom:lab` passthrough, including tagged model ids.
- Explicit `@local:<model>`, `@ollama:<model>`, and every real provider id.
- A valid `providers.custom-configured` entry: `@custom-configured:<model>`
  resolves to that named provider and its endpoint.
- A malformed non-mapping `providers.<slug>` entry does not raise; unrelated
  routes are unaffected.
- The bare `custom` passthrough when `model.provider` is also `custom` stays
  bare (maintainer-pinned under #7356) and can still be claimed by a competing
  `custom_providers[]` entry that lists the model.

## Known ambiguity

Under a custom-endpoint lane, a stale named-provider reference
`@custom:<unconfigured-slug>:<model>` now resolves the whole payload as a model
id on the configured endpoint, where it previously resolved to
`('custom:<slug>', None)` and failed at runtime with `not configured`. The
token is genuinely ambiguous — a local-server model id can look like
`slug:tag` — and the endpoint-authoritative reading is the one this contract
mandates. When the active provider is a named `custom:<slug>`, that
reference still fails closed (rule 5 above).

## Tests

`tests/test_issue7955_custom_lane_endpoint_authoritative.py` drives the real
encode → resolve path against a real `config.yaml` (no mocks). It covers the
acceptance matrix above (both competitor shapes, the `ollama`/`vllm`/legacy
`local` spellings, the same-named-record rows, the mixed-authority `local`
entry), the unchanged routes, the malformed-entry negative control, and the
disjointness rules — including a token that names a colon-bearing `providers:`
key (`custom:a:b`) and one that names a `custom_providers[]` slug, both of which
must keep their pre-existing route.

It does not enumerate the full product of rows × spellings × competitor shapes,
and the wider differential probe used while developing this change is not
committed. `tests/test_issue1806_named_custom_provider_resolution.py` pins the
#4728 fail-closed rule this contract preserves.