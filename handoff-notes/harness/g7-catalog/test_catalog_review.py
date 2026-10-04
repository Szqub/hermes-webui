"""Disposable read-only route counterexample probes; synthetic URLs only."""
import sys
from pathlib import Path
import pytest

REPO = Path('/opt/data/cache/scratch/wt-design-7955')
sys.path.insert(0, str(REPO))
BASE = 'http://127.0.0.1:11434/v1'
OTHER = 'http://record.invalid:9999/v1'
MID = 'qwen3:8b'

CASES = [
    ('model_custom', {'model': {'provider': 'custom', 'base_url': BASE}}),
    ('model_custom_record_custom', {'model': {'provider': 'custom', 'base_url': BASE}, 'providers': {'custom': {'base_url': OTHER, 'models': [MID]}}}),
    ('ollama_record_custom', {'model': {'provider': 'ollama', 'base_url': BASE}, 'providers': {'custom': {'base_url': OTHER, 'models': [MID]}}}),
    ('no_model_base_record_custom', {'model': {'provider': 'custom'}, 'providers': {'custom': {'base_url': OTHER, 'models': [MID]}}}),
    ('no_model_base_no_record', {'model': {'provider': 'custom'}}),
    ('active_named', {'model': {'provider': 'custom:lab', 'base_url': BASE}, 'custom_providers': [{'name': 'lab', 'base_url': OTHER, 'models': [MID]}]}),
    ('entry_named_custom', {'model': {'provider': 'ollama', 'base_url': BASE}, 'custom_providers': [{'name': 'custom', 'base_url': OTHER, 'models': [MID]}]}),
    ('model_custom_entry_named_custom', {'model': {'provider': 'custom', 'base_url': BASE}, 'custom_providers': [{'name': 'custom', 'base_url': OTHER, 'models': [MID]}]}),
    ('nonlocal_active', {'model': {'provider': 'openai', 'base_url': BASE}}),
    ('named_local_active', {'model': {'provider': 'custom:ollama', 'base_url': BASE}, 'custom_providers': [{'name': 'ollama', 'base_url': OTHER, 'models': [MID]}]}),
]

@pytest.fixture
def config(monkeypatch):
    from api import config
    monkeypatch.setattr(config, 'cfg', {})
    monkeypatch.setattr(config, '_is_plugin_model_provider', lambda _: False)
    return config


def resolved(config, wire):
    try:
        return config.resolve_model_provider(wire)
    except ValueError as exc:
        return f'{type(exc).__name__}: {exc}'


@pytest.mark.parametrize('label,data', CASES, ids=[x[0] for x in CASES])
def test_matrix(config, label, data):
    config.cfg = data
    wire = config._encode_catalog_route(MID, 'custom')
    forward = resolved(config, wire)
    reserved = resolved(config, '@!:' + MID)
    reverse = config._encode_catalog_route(reserved[0], reserved[1]) if isinstance(reserved, tuple) else 'unavailable'
    session = config.model_with_provider_context(MID, 'custom')
    print(f'\n{label}: reserved_predicate={config._configured_custom_lane_is_reserved()} catalog={wire!r} resolves={forward!r} reserved_resolves={reserved!r} reencoded={reverse!r} session={session!r} session_resolves={resolved(config, session)!r}')
    if label == 'entry_named_custom':
        named = config._custom_provider_slug_from_name('custom')
        named_wire = config._encode_catalog_route(MID, named)
        print(f'named-entry-control: provider={named!r} wire={named_wire!r} resolves={resolved(config, named_wire)!r}')
    assert isinstance(wire, str)


def test_configured_custom_catalog_should_roundtrip(config):
    config.cfg = {'model': {'provider': 'custom', 'base_url': BASE}}
    assert config.resolve_model_provider(config._encode_catalog_route(MID, 'custom')) == (MID, 'custom', BASE)


def test_generic_custom_record_should_keep_record(config):
    config.cfg = {'model': {'provider': 'ollama', 'base_url': BASE}, 'providers': {'custom': {'base_url': OTHER, 'models': [MID]}}}
    assert config.resolve_model_provider(config._encode_catalog_route(MID, 'custom')) == (MID, 'custom', OTHER)


def test_catalog_predicate_should_agree_with_reserved_resolver(config):
    config.cfg = {'model': {'provider': 'custom', 'base_url': BASE}}
    result = config.resolve_model_provider('@!:' + MID)
    assert config._encode_catalog_route(result[0], result[1]) == '@!:' + MID


@pytest.mark.parametrize('active', ['ollama', 'custom', 'custom:lab'])
@pytest.mark.parametrize('mid', ['mistral-7b', 'qwen3:8b'])
def test_real_static_catalog(config, monkeypatch, active, mid):
    from api import providers
    monkeypatch.setattr(providers, '_provider_has_key', lambda _: False)
    monkeypatch.setattr(config, '_plugin_model_provider_profiles', lambda: {})
    config.cfg = {'model': {'provider': active, 'base_url': BASE, 'default': 'default-only'}, 'providers': {'custom': {'base_url': OTHER, 'models': [mid]}}}
    if active.startswith('custom:'):
        config.cfg['custom_providers'] = [{'name': 'lab', 'base_url': BASE, 'models': ['default-only']}]
    catalog = config._static_models_catalog_without_live_probes()
    options = [(g['provider_id'], m['id'], resolved(config, m['id'])) for g in catalog.get('groups', []) for m in g.get('models', []) if mid in m['id']]
    print(f'\nstatic-catalog active={active!r} mid={mid!r}: {options!r}')
    assert any(provider == 'custom' for provider, _, _ in options)


def test_plain_generic_custom_record_should_keep_record(config):
    config.cfg = {'model': {'provider': 'ollama', 'base_url': BASE}, 'providers': {'custom': {'base_url': OTHER, 'models': ['mistral-7b']}}}
    wire = config._encode_catalog_route('mistral-7b', 'custom')
    assert config.resolve_model_provider(wire) == ('mistral-7b', 'custom', OTHER)


@pytest.mark.parametrize('with_base', [True, False])
def test_real_catalog_record_collision(config, monkeypatch, with_base):
    from api import providers
    monkeypatch.setattr(providers, '_provider_has_key', lambda _: False)
    monkeypatch.setattr(config, '_plugin_model_provider_profiles', lambda: {})
    model = {'provider': 'ollama', 'default': 'default-only'}
    if with_base:
        model['base_url'] = BASE
    mid = 'vendor/qwen3:8b'
    config.cfg = {'model': model, 'providers': {'aaa': {'base_url': 'http://aaa.invalid/v1', 'models': [mid]}, 'custom': {'base_url': OTHER, 'models': [mid]}}}
    catalog = config._static_models_catalog_without_live_probes()
    options = [(g['provider_id'], m['id'], resolved(config, m['id'])) for g in catalog['groups'] for m in g.get('models', []) if mid in m['id']]
    print(f'\nreal-collision with_base={with_base}: {options!r}')
    option = next(m['id'] for g in catalog['groups'] if g['provider_id'] == 'custom' for m in g['models'] if mid in m['id'])
    assert config.resolve_model_provider(option) == (mid, 'custom', OTHER)
