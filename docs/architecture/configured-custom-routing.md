# Configured Custom routing grammar

Status: implemented for #7955.

## Authority and wire forms

The session selection owns the provider lane. The active configuration's
`model.base_url` owns the configured endpoint; an overlapping catalog entry
must not replace it. The wire representation is internal routing metadata,
not an upstream identifier.

- `@!:M` is the configured Custom lane. Everything after the first three
  characters is the opaque identifier M, including slashes and any colons.
- `@E(P):M` is a generic provider route. P is trimmed and lower-cased.
  E preserves `[a-z0-9_.~-]+`, `custom:` followed by that alphabet, and
  `custom:host:port` when host uses that alphabet, host is localhost or contains
  a dot, and port is an ASCII decimal integer from 1 through 65535.
  Otherwise E percent-encodes the UTF-8 provider string. The unescaped
  punctuation matches JavaScript `encodeURIComponent`, except `!` MUST also
  be encoded. `%` is always encoded. An empty provider emits no wrapper.
- A percent-bearing generic provider segment is decoded exactly once, up to
  the first literal colon. Its entire suffix remains opaque, never URL-decoded.
- Legacy unescaped `custom:slug` takes one slug segment; endpoint-style
  `custom:host:port` takes two. The remainder is the complete identifier.
  Other legacy provider spellings retain the existing parser fallback.

Python's `_encode_provider_qualified_model_id` and JavaScript's
`_encodeModelRoute` produce generic routes. `_parse_provider_qualified_model_id`
and `_parseModelRoute` consume the reserved and escaped forms before legacy
parsing. Known provider metadata can disambiguate legacy browser values.

## Disjointness proof

Partition generic provider inputs into empty, legacy-safe, and escaped:

1. Empty emits no provider wrapper.
2. Legacy-safe strings contain no `!` or `%`.
3. Every `!` in the escaped class becomes `%21`; every literal percent becomes
   `%25`. This includes a provider literally named `!`, `!:x`, or `%21`.

Therefore no generic provider wrapper begins `@!:`. The reserved decoder tests
that literal prefix BEFORE percent decoding, so decoding `%21` cannot enter
it. Neither provider length, case, embedded colons, whitespace, nor the suffix
can change the prefix proof. No provider name is forbidden and no unlikely
reserved provider spelling is assumed. Existing qualified input is passed
through, not treated as an instruction to manufacture a generic wrapper.

Tests exercise `custom`, `custom:a:b`, `Custom:Lab`, `+x`, `%2Bx`, `foo bar`,
`foo:bar:baz`, empty and whitespace-only strings, surrounding whitespace,
non-string values, a 10,000-character identifier, `!`, `!:payload`, `a!b`,
`@!:`, and marker/percent-bearing host-like identifiers. They use the actual
catalog prefix producer, generic encoder, resolver, and executable JavaScript.
Configured record membership uses canonical provider identity, not raw key case.

## Resolution order

1. Recognize `@!:` directly, before configured-provider alias resolution,
   ownership scans, and the generic parser. Return the whole suffix, `custom`,
   and `model.base_url`. No `providers.ollama`, `providers.local`, or named
   custom record participates. Missing endpoint, empty suffix, or an active
   named `custom:slug` fails closed instead of borrowing an ambient endpoint.
2. Non-reserved values retain configured/default ownership and catalog scans.
3. Parse generic qualified routes and resolve their own record, preserving
   named-custom uniqueness checks and endpoint-derived local aliases.
4. Retain slash routing and existing unqualified fallback behavior.

The Python session encoder emits the reserved route when the selected lane is
`custom`, the configured provider is a local-server provider (including Ollama,
vLLM, LM Studio and llama.cpp) or legacy `local`, and a base URL exists.
Explicit browser Custom selections also produce it. Generic catalog records,
including a record named `custom`, use only the generic encoder. Existing
same-provider bare Custom passthrough remains unchanged on the Python path.

## Acceptance matrix

Configured base: `http://127.0.0.1:11434/v1`. Run the overlap rows for each of
`ollama`, `vllm`, `lmstudio`, `llamacpp`, and `local`, and for both
`custom_providers: [{name: lab, ...}]` and `providers: {lab: ...}`.

| Selection | Expected route |
| --- | --- |
| Custom `mistral-7b`, also offered by competitor | whole identifier, `custom`, configured base |
| Custom `qwen3.8:27b`, also offered by competitor | whole identifier, `custom`, configured base |
| Custom `qwen3:8b`, named competitor `qwen3` | whole identifier, `custom`, configured base |
| Ollama-only `llama3`, Ollama lane | `llama3`, `ollama`, configured base |
| Custom with `providers.ollama.base_url: http://other:9999` | configured base; override not consulted |
| Legacy local with `providers.local.base_url: http://other:9999` | configured base; override not consulted |
| Legacy local with named `local` at `http://named:7777/v1` | configured base; named credential not borrowed |
| Named `custom:slug` selection | named endpoint, not configured Custom lane |
| Explicit `@local:llama3` or `@ollama:llama3` | original explicit provider rules |
| `providers.custom-configured` | ordinary generic record |
| Endpoint-derived `custom:host:port` | existing configured-local alias rule |
| Missing named slug under active named custom provider | no ambient endpoint (#4728) |

## Persisted legacy strings

No automatic migration guesses the origin of `@custom:qwen3:8b`. Read on its
own — the wire parse, with no lane context — it still means identifier `8b` on
named provider `custom:qwen3`; if that record exists, it resolves there, and if
absent it retains the missing-provider outcome. The picker reads it differently
only when it knows the option was listed under the plain `custom` lane, in which
case the whole remainder is the identifier. A plain `@custom:mistral-7b` remains
a generic Custom hint. Re-selecting the configured Custom entry writes the
unambiguous representation. This preserves deliberate named selections instead
of silently stealing them to repair indistinguishable old Custom picks.

A caller-supplied provider hint decides only when it matches the value exactly.
The browser restore path may know that the stored lane was `custom`, which is
exactly the ambiguity `@custom:qwen3:8b` cannot answer on its own; re-reading it
as the configured lane would show one endpoint in the picker while the runtime
resolved another. So an exact hint prefix is honoured first, and the legacy split
runs only when no hint matches — which keeps both languages in agreement about
what an unhinted stored value names. A restored value is injected verbatim.
Reaching the configured endpoint for a stored colon-bearing identifier requires
re-selecting the entry.

Option lookup, session restore and picker state all follow the same rule: the
lane named by the matched option decides the prefix, because the catalog sets an
option's `data-provider` to the group that listed it. A plain Custom-lane option
is therefore `@custom:<model>` in group `custom`, and the whole remainder is the
identifier — splitting at the first colon would read a colon-bearing id as a
record name and truncate it to `8b`. A value read under a named record
(`@custom:backup:model-a` with hint `custom:backup`) still resolves to that
record and model `model-a`, so a stored value is never substituted by an
identically-named option belonging to another provider.

The catalog cooperates instead of relying on that precedence: an option for the
configured lane is emitted as `@!:M`, never as `@custom:M`, because the latter
spelling also names a record and a colon-bearing identifier would be read back
as a record reference. `_encode_catalog_route` applies this whenever the active
configuration really owns the reserved lane (base URL present, provider a local
server or legacy `local`); every other provider keeps the generic escaped route,
and a configuration without that endpoint keeps the generic spelling too, so the
catalog can never advertise a route the resolver would reject.
Multiple suffix segments now follow the same non-greedy named/host-port rule in
Python and JavaScript.

Old unescaped exotic provider names containing percent escape sequences cannot
be distinguished from the new escaped form. Re-selecting them uses `%25` and
round-trips without double decoding. A historic provider literally named `!`
used `@!:...`; that old string now denotes the reserved lane. Re-selecting the
ordinary `!` record emits `@%21:...`. There is no lossless migration without
separate provenance. Downgrading also cannot interpret new reserved tokens.

## Consumers and verification boundary

Catalog prefixing, deduplication, badges, core catalog seeding and session
encoding share the generic producer. Profile normalization, gateway payloads,
request lane comparison and runtime observation share the Python parser.
Reasoning and auxiliary persistence recognize the new forms. Browser aliases,
picker identity, restore/injection, live entries, display labels and cron
persistence use the browser grammar. Fixed `@nous:` literals are legacy-safe;
normalizers which only remove the first colon already preserve reserved and
escaped suffixes and retain their existing hierarchy behavior.

The regression suite exercises synthetic endpoints only. No live upstream
request is required to prove encoding or endpoint selection. Layout and visual
behavior are not changed; the JavaScript checks execute picker functions with
small DOM substitutes, not a visual browser session.
