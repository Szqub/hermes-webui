# Provider-context model encoding contract (`model_with_provider_context`)

This document records the runtime contract for the model-id encoding boundary
between a stored session and the resolver:

```
session (model, model_provider)
        │
        ▼
model_with_provider_context(model, model_provider)   # api/config.py
        │  returns a bare id or an "@provider:model" hint
        ▼
resolve_model_provider(encoded)                      # api/config.py
        │  returns (model, provider, base_url)
        ▼
streaming / Gateway request construction
```

It describes shipped behavior: the resolver's grammar, the evaluation order of
the encoder, and the rules the two halves have to agree on. It was added because
the #7955 review flagged the encoding rules as undocumented — the behaviour
lives entirely in code comments inside `model_with_provider_context()` and
`_parse_provider_qualified_model_id()`.

Start here before changing how a session's provider is folded into the request
model id, before adding a new provider kind to the picker, or before touching
`_parse_provider_qualified_model_id()`.

## Why the indirection exists

A session persists the user's selected provider separately in
`model_provider` rather than forcing every selection into `@provider:model`
form. The resolver still understands that internal disambiguation form, so the
encoder uses it **only when the provider context is needed to route away from
the configured default**. Emitting the hint when the configured default already
routes the model is what lets a provider-specific `base_url` / proxy setting
stay in charge.

## The grammar

`_parse_provider_qualified_model_id()` is the shared reader. It exists because
both halves of the encoding are ambiguous: a provider segment can contain
colons (named custom providers), and a model segment can contain colons
(`:free` / `:thinking` tags, `host:port` authorities, Ollama-style
`model:tag` ids). The reader therefore:

1. `rsplit(":", 1)` to peel the model off the provider prefix;
2. peels one more segment back when the provider segment is a `custom:<slug>`
   that does not look like `host:port`;
3. falls back to `split(":", 1)` only when the first candidate is not a known
   provider and is not a `custom:` slug.

Consequences the encoder must respect:

- **A bare `custom` prefix is only valid when it is the route.** `custom` with no
  slug is the generic OpenAI-compatible pseudo-provider. Its endpoint comes from
  `model.base_url` — or from `providers.custom.base_url` when the config
  declares one (`_get_provider_base_url()` reads either). Only the first is the
  same endpoint as the configured provider, so only then is the hint
  meaningless; when `providers.custom` owns a `base_url`, `@custom:<model>` is a
  real route and dropping it sends the request to the configured default
  provider instead.
  Minting the hint for the same-endpoint case is lossy for any colon-bearing id:
  the reader takes the model's own first colon token as a named-provider slug.
  For `qwen3.8:27b` the round trip is:

  ```
  model_with_provider_context("qwen3.8:27b", "custom")  -> "@custom:qwen3.8:27b"
  resolve_model_provider("@custom:qwen3.8:27b")         -> ("27b", "custom:qwen3.8", None)
  ```

  No `custom_providers[]` entry owns `custom:qwen3.8`, so the request fails as
  an unconfigured custom provider (#7955). Hence: stay bare when both sides name
  the same endpoint, and only then.

- **A named `custom:<slug>` is a real route** and must keep its explicit hint;
  the reader's step-2 peel handles its colon-bearing model ids.

## Rules, in evaluation order

`model_with_provider_context(model_id, model_provider)` returns the input
unchanged when the model or provider is empty, the provider is `default`, or
the id is already `@`-prefixed. Otherwise, in order:

1. **ACP subprocess providers** (`cursor-acp`, `copilot-acp`) — always
   `@provider:model`; their slash ids are not OpenRouter paths.
2. **Plugin model providers** — always `@provider:model`. This precedes the
   configured-provider passthrough deliberately: a plugin provider that is
   *also* the configured provider would otherwise lose its hint and the model
   would be sent to the wrong backend (#5909).
3. **`openai-codex`** — always `@provider:model`; its live/cache models are
   absent from the static catalog and can be claimed by overlapping
   `providers.*` entries.
4. **Provider equals the configured provider** — bare passthrough, preserving
   the configured `base_url` / proxy.
5. **Bare `custom`, or its legacy `local` alias, naming the same endpoint as the
   config** — bare passthrough. The picker stores exactly that slug when the
   alias tables collapse the active provider to it
   (`_resolve_configured_provider_id()`), and also when the config names no
   provider but sets a `base_url` (the Custom-group fallback). The step-4
   comparison is a raw string comparison and misses the pair, so the model stays
   bare and the configured provider — or its `base_url` — routes it (#7955).
   Guarded on both sides: `providers.custom` / `providers.local` declaring their
   own `base_url` makes `@custom:<model>` a real route, and a config provider
   that is neither local nor collapsed by the alias tables (say `anthropic`) is
   a different endpoint, so both keep the explicit hint.
6. **OpenRouter** — `@openrouter:model`; slash ids are explicit
   provider/model paths.
7. **Provider declared under `providers:`** — `@provider:model`, so a local
   model with a HuggingFace-style id keeps its hint instead of inheriting the
   default provider.
8. **Slash-bearing model id** — `@provider:model` for known static/portal
   providers and for `custom:<slug>` ids that resolve to a unique
   `custom_providers[]` entry; otherwise the bare id, so custom/proxy
   `base_url` routing stays in charge (#7333, #7356).
9. **Everything else** — `@provider:model`.

## Invariants

- **Round-trip integrity for colon-bearing ids:** when the encoder leaves an id
  bare, no part of the model id may be read as a provider slug — the resolver
  must return the model string the caller passed, not a suffix of it. (Two known
  limits, both outside this rule's scope: the resolver may normalise away a
  redundant `@provider:` hint that merely repeats the configured provider, which
  is prefix stripping rather than model truncation; and a colon-bearing id under
  a declared `providers.custom` endpoint still round-trips lossily through
  `@custom:<id>`, because the reader cannot tell that slug from the model's own
  first colon token.)
- **One endpoint per decision:** when the session provider and the configured
  provider name the same endpoint, the encoder must not mint a hint — the
  configured provider's `base_url` decides.
- **Named routes stay explicit:** `custom:<slug>` selections keep their hint so
  the credential lookup can pair the right endpoint with the right key.
- **Negative control:** a slug that is neither the configured provider, a local
  server, nor a bare `custom`/`local` keeps its explicit hint (rule 9) rather
  than being folded into the default provider.

Regression coverage: `tests/test_issue7955_bare_custom_local_provider_model_id.py`
(round trip, the bare-`custom`/`local` rule across config names, the
empty-provider variant, the declared `providers.custom`/`providers.local`
endpoint that must keep its hint, and the named-slug / unknown-slug guards), plus
the encoding suites `tests/test_issue7333_slash_id_provider_hint.py`,
`tests/test_model_resolver.py`, `tests/test_provider_mismatch.py`, and
`tests/test_issue1894_provider_overlap.py`.
