# long-running-project (Grok skill)

Part of **[GLRP Skill](https://github.com/msinclair25/GLRP-Skill)** — see the repository root README for install and usage.

## Quick invoke

```text
activate long running project
/long-running-project
```

## Local paths after install

```text
${GROK_HOME:-$HOME/.grok}/skills/long-running-project/
```

## Scaffold only

```bash
python3 "${GROK_HOME:-$HOME/.grok}/skills/long-running-project/scripts/scaffold.py" --cwd /path/to/repo
```

## Grok 4.7 compatibility

Verified with Grok Build CLI 1.0.41 and the live Grok 4.7 / Grok 4.7 Build Fast catalog entries. After scaffolding, review the status/diff and open a new Grok session in the project; approve folder trust so project rules and config load. Existing `.grok/config.toml` files are never overwritten: when one is present, the scaffold reports that GLRP's deny rules were not merged and prints the comparison-template path. The full playbook is copied into the project instead of linked to the installing machine.
