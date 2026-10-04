"""Executable browser route grammar coverage for #7955 (no browser services)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node not available")

DRIVER = r"""
const fs=require('fs');
const root=process.argv[2];
const ui=fs.readFileSync(root+'/static/ui.js','utf8');
const commands=fs.readFileSync(root+'/static/commands.js','utf8');
const panels=fs.readFileSync(root+'/static/panels.js','utf8');
function extract(source,name){
  const start=source.indexOf('function '+name+'(');
  if(start<0) return '';
  const next=/\n(?:async )?function \w+\(/g;
  next.lastIndex=start+1;
  const end=next.exec(source);
  const block=source.slice(start,end?end.index:source.length);
  return block.slice(0,block.lastIndexOf('\n}')+2);
}
const window={_configuredModelBadges:{},_activeProvider:''};
const S={session:null};
const _dynamicModelLabels={};
const _liveModelFetchPending=new Set();
const $=()=>null;
const syncModelChip=()=>{};
const _fmtOllamaLabel=s=>s;
const _stripDottedModelPrefix=s=>s;
for(const name of ['_encodeModelRoute','_parseModelRoute','_getOptionProviderId',
  '_providerFromModelValue','_modelPickerOptionIdentity','_modelStateForSelect',
  '_deduplicateModelPickerOptions','_findModelInDropdown','_refreshOpenModelDropdown',
  '_applyModelToDropdown','_ensureModelOptionInDropdown','_addLiveModelsToSelect',
  '_normalizeConfiguredModelKey','_isEquivalentConfiguredModelEntry','getModelLabel']){
  eval(extract(ui,name));
}
eval(extract(commands,'_resolveModelAliasTarget'));
eval(extract(panels,'_modelBareNameForProvider'));
class Element {
  constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.value='';this.id='';this.label='';}
  appendChild(child){child.parentElement=this;this.children.push(child);return child;}
  removeChild(child){this.children=this.children.filter(c=>c!==child);}
  querySelectorAll(tag){return this.children.filter(c=>c.tagName===tag.toUpperCase());}
  get options(){return this.children.flatMap(c=>c.tagName==='OPTGROUP'?c.children:[c]);}
  get selectedOptions(){return this.options.filter(c=>c.value===this.value);}
}
const document={createElement:tag=>new Element(tag)};
function select(value,provider){
  const sel=new Element('select');
  const group=sel.appendChild(new Element('optgroup'));group.dataset.provider=provider;
  const opt=group.appendChild(new Element('option'));opt.value=value;opt.dataset.provider=provider;
  sel.value=value;return sel;
}
const input=JSON.parse(process.argv[3]);
let result;
if(input.action==='consumers'){
  result=input.cases.map(([route,provider,model])=>{
    const sel=select(route,provider);
    return {provider:_providerFromModelValue(route),optionProvider:_getOptionProviderId({value:route}),
      identity:_modelPickerOptionIdentity(route,provider),state:_modelStateForSelect(sel,route),
      bare:_modelBareNameForProvider(route,provider),label:getModelLabel(route),
      match:_findModelInDropdown(model,sel,provider),
      badgeEquivalent:_isEquivalentConfiguredModelEntry(route,{provider},[{value:model,providerId:provider}])};
  });
}else if(input.action==='encode'){
  result=input.cases.map(([provider,model])=>_encodeModelRoute(provider,model));
}else if(input.action==='aliases'){
  result=input.targets.map(target=>_resolveModelAliasTarget(input.options||[],input.providerMap||{},target));
}else if(input.action==='inject'){
  result=input.cases.map(([provider,model])=>{
    const sel=new Element('select');
    const value=_ensureModelOptionInDropdown(model,sel,provider);
    return {value,state:_modelStateForSelect(sel,value),label:getModelLabel(value)};
  });
}else if(input.action==='inject-existing'){
  result=input.cases.map(([provider,model,preexisting])=>{
    const sel=new Element('select');
    const group=sel.appendChild(new Element('optgroup'));
    group.dataset.provider=String(provider).split(':')[0];
    for(const value of (preexisting||[])){
      const opt=group.appendChild(new Element('option'));
      opt.value=value;opt.dataset.provider=String(provider).split(':')[0];
    }
    const applied=_ensureModelOptionInDropdown(model,sel,provider);
    return {applied,selected:sel.value,options:sel.options.map(o=>o.value),
      state:_modelStateForSelect(sel,sel.value)};
  });
}else if(input.action==='live'){
  result=input.cases.map(([provider,model])=>{
    window._activeProvider=provider;
    const sel=new Element('select');
    _addLiveModelsToSelect(provider,[{id:model}],sel);
    const value=sel.options[0].value;
    return {value,state:_modelStateForSelect(sel,value)};
  });
}else if(input.action==='parse'){
  result=input.cases.map(([route,provider])=>_parseModelRoute(route,provider));
}
console.log(JSON.stringify(result));
"""


def run_js(tmp_path, action, **payload):
    assert NODE is not None
    driver = tmp_path / "routes.js"
    driver.write_text(DRIVER)
    proc = subprocess.run(
        [NODE, str(driver), str(ROOT), json.dumps(dict(action=action, **payload))],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_python_browser_encoder_parity(tmp_path):
    from api import config
    ids = ['custom', 'custom:a:b', 'Custom:Lab', '+x', '%2Bx', 'foo bar',
           'foo:bar:baz', '', '  ', '  Custom:Lab  ', 123, None, 'x' * 10000,
           '!', '!:payload', 'a!b', '@!:', 'custom:!.example:8080',
           'custom:%21.example:8080', 'custom:a:123', 'custom:host:99999']
    cases = [[provider, 'Qwen:8b:free'] for provider in ids]
    expected = [config._encode_provider_qualified_model_id(mid, provider) for provider, mid in cases]
    assert run_js(tmp_path, 'encode', cases=cases) == expected


def test_dedicated_and_escaped_routes_keep_full_model_suffix(tmp_path):
    cases = [
        ["@!:qwen3:8b", "custom", "qwen3:8b"],
        ["@!:vendor/qwen3:8b:free", "custom", "vendor/qwen3:8b:free"],
        ["@custom%3Agateway%3Aeast:vendor/qwen3:8b:free", "custom:gateway:east", "vendor/qwen3:8b:free"],
        ["@custom%3Amy%20gateway:Qwen3:8b", "custom:my gateway", "Qwen3:8b"],
        ["@custom%3A100%25:Qwen3:8b", "custom:100%", "Qwen3:8b"],
        ["@custom%3A%21:Qwen3:8b", "custom:!", "Qwen3:8b"],
        ["@custom:backup:vendor/qwen3:8b", "custom:backup", "vendor/qwen3:8b"],
        ["@custom:localhost:11434:qwen3:8b", "custom:localhost:11434", "qwen3:8b"],
    ]
    results = run_js(tmp_path, "consumers", cases=cases)
    for (route, provider, model), result in zip(cases, results):
        assert result == dict(
            provider=provider, optionProvider=provider, identity=model.lower(),
            state=dict(model=model, model_provider=provider), bare=model, label=model,
            match=route, badgeEquivalent=True,
        )


def test_generic_encoder_is_canonical_and_never_uses_dedicated_marker(tmp_path):
    cases = [
        [" OpenAI ", "qwen3:8b"], ["custom", "qwen3:8b"],
        ["custom:backup", "a:b"], ["custom:localhost:11434", "a:b"],
        ["custom:east:west", "a:b"], ["my gateway", "a:b"],
        ["!", "a:b"], ["%21", "a:b"], ["custom:!", "a:b"],
        ["网关", "a:b"], ["", "a:b"], [None, "a:b"], [42, "a:b"],
    ]
    expected = [
        "@openai:qwen3:8b", "@custom:qwen3:8b", "@custom:backup:a:b",
        "@custom:localhost:11434:a:b", "@custom%3Aeast%3Awest:a:b",
        "@my%20gateway:a:b", "@%21:a:b", "@%2521:a:b", "@custom%3A%21:a:b",
        "@%E7%BD%91%E5%85%B3:a:b", "a:b", "a:b", "@42:a:b",
    ]
    assert run_js(tmp_path, "encode", cases=cases) == expected
    assert not any(value.startswith("@!:") for value in expected)


def test_alias_objects_use_dedicated_only_for_custom_lane(tmp_path):
    targets = [dict(route_provider=" Custom ", model="qwen3:8b"),
               dict(route_provider="custom:east:west", model="vendor/qwen3:8b"),
               dict(route_provider="!", model="a:b"), "custom/qwen3:8b"]
    assert run_js(tmp_path, "aliases", targets=targets) == [
        dict(value="@!:qwen3:8b", provider="custom"),
        dict(value="@custom%3Aeast%3Awest:vendor/qwen3:8b", provider="custom:east:west"),
        dict(value="@%21:a:b", provider="!"),
        dict(value="@custom:qwen3:8b", provider="custom"),
    ]


def test_injection_uses_select_context_and_live_uses_generic_encoder(tmp_path):
    cases = [["custom", "qwen3:8b"], ["custom:east:west", "vendor/qwen3:8b"]]
    assert run_js(tmp_path, "inject", cases=cases) == [
        dict(value="@!:qwen3:8b", state=dict(model="qwen3:8b", model_provider="custom"), label="qwen3:8b"),
        dict(value="@custom%3Aeast%3Awest:vendor/qwen3:8b", state=dict(model="vendor/qwen3:8b", model_provider="custom:east:west"), label="vendor/qwen3:8b"),
    ]
    assert run_js(tmp_path, "live", cases=[["custom:east:west", "vendor/qwen3:8b"]]) == [
        dict(value="@custom%3Aeast%3Awest:vendor/qwen3:8b", state=dict(model="vendor/qwen3:8b", model_provider="custom:east:west")),
    ]


def test_generic_decoding_is_single_pass_and_does_not_decode_model(tmp_path):
    assert run_js(tmp_path, "parse", cases=[
        ["@%21:a%3Ab:c"], ["@%2521:a:b"], ["@vendor%3Aeast:host/model:tag"],
        ["@!:qwen3:8b", "custom:qwen3"], ["@bad%ZZ:model:tag"],
        ["@custom:qwen3:8b", "custom"], ["qwen3:8b"],
    ]) == [
        dict(provider="!", model="a%3Ab:c"), dict(provider="%21", model="a:b"),
        dict(provider="vendor:east", model="host/model:tag"), dict(provider="custom", model="qwen3:8b"),
        dict(provider="bad%zz", model="model:tag"), dict(provider="custom", model="qwen3:8b"), None,
    ]


def test_alias_lookup_reuses_escaped_and_dedicated_catalog_routes(tmp_path):
    routes = ["@!:qwen3:8b", "@custom%3Aeast%3Awest:vendor/qwen3:8b"]
    providers = ["custom", "custom:east:west"]
    assert run_js(
        tmp_path, "aliases", targets=["custom/qwen3:8b", "custom:east:west/vendor/qwen3:8b"],
        options=[dict(value=value) for value in routes],
        providerMap=dict(zip(routes, providers)),
    ) == [dict(value=value, provider=provider) for value, provider in zip(routes, providers)]


def test_noncustom_routes_keep_explicit_namespace_in_session_state(tmp_path):
    cases = [["@%21:qwen3:8b", "!", "qwen3:8b"],
             ["@vendor%3Aeast:vendor/qwen3:8b", "vendor:east", "vendor/qwen3:8b"],
             ["@safe:qwen3:8b", "safe", "qwen3:8b"]]
    for (route, provider, model), result in zip(cases, run_js(tmp_path, "consumers", cases=cases)):
        assert result["provider"] == provider
        assert result["optionProvider"] == provider
        assert result["state"] == dict(model=route, model_provider=provider)
        assert result["bare"] == model
        assert result["match"] == route


def test_injecting_existing_route_never_double_wraps_or_decodes_suffix(tmp_path):
    cases = [["custom", "@!:qwen3:8b"],
             ["custom", "@custom:qwen3:8b"],
             ["custom:east:west", "@custom%3Aeast%3Awest:Qwen%3A3:8b"]]
    out = run_js(tmp_path, "inject", cases=cases)
    # A colon-bearing legacy value is injected verbatim: parsing must not move
    # it to the configured lane, or restore would silently change the endpoint.
    assert [row["value"] for row in out] == [
        "@!:qwen3:8b", "@custom:qwen3:8b", "@custom%3Aeast%3Awest:Qwen%3A3:8b",
    ]
    # The option's own lane decides the prefix: the catalog lists a plain
    # Custom-lane model as `@custom:<model>` in group `custom`, so the whole
    # remainder is the model id. Reading the first colon as a record separator
    # would truncate it to `8b` and route to a provider that does not exist.
    assert [row["state"]["model"] for row in out] == ["qwen3:8b", "qwen3:8b", "Qwen%3A3:8b"]
    assert [row["state"].get("model_provider") for row in out] == ["custom", "custom", "custom:east:west"]


def test_legacy_value_is_not_substituted_by_a_configured_lane_option(tmp_path):
    """A stored legacy value keeps its own provider during option lookup.

    The dropdown may already hold the configured-lane option `@!:8b`, whose
    parsed identifier is the same `8b`. Matching on the identifier alone would
    swap the stored value for a different provider's option and move the
    endpoint on restore, so the provider carried by the value must win.
    """
    out = run_js(tmp_path, "inject-existing", cases=[
        ["custom", "@custom:qwen3:8b", ["@!:8b"]],
        ["custom", "@custom:qwen3:8b", []],
        ["custom:qwen3", "@custom:qwen3:8b", ["@!:8b"]],
        ["custom", "@!:qwen3:8b", ["@!:qwen3:8b"]],
    ])
    assert [row["applied"] for row in out] == [
        "@custom:qwen3:8b", "@custom:qwen3:8b", "@custom:qwen3:8b", "@!:qwen3:8b",
    ]
    assert [row["selected"] for row in out] == [
        "@custom:qwen3:8b", "@custom:qwen3:8b", "@custom:qwen3:8b", "@!:qwen3:8b",
    ]
    # The lane named by the option decides: a plain Custom-lane value keeps the
    # whole remainder as the model id, while a value read under the named record
    # `custom:qwen3` really does name model `8b` there.
    assert [row["state"]["model"] for row in out] == ["qwen3:8b", "qwen3:8b", "8b", "qwen3:8b"]
    assert [row["state"]["model_provider"] for row in out] == [
        "custom", "custom", "custom:qwen3", "custom",
    ]


def test_configured_lane_option_carries_the_reserved_route(tmp_path):
    """The configured lane is advertised as `@!:` so the picker keeps the id.

    The catalog must not list the configured lane as `@custom:<id>`: that
    spelling also names a record, so a colon-bearing identifier would be read
    back as a record reference and the picker would send a truncated id to a
    different endpoint (#7955).
    """
    out = run_js(tmp_path, "consumers", cases=[
        ["@!:qwen3:8b", "custom", "qwen3:8b"],
        ["@custom:backup:model-a", "custom:backup", "backup:model-a"],
    ])
    assert [(row["state"]["model"], row["state"]["model_provider"]) for row in out] == [
        ("qwen3:8b", "custom"),
        ("model-a", "custom:backup"),
    ]
