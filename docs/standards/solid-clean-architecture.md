---
title: SOLID and Clean Architecture standard
status: active
author: Garrett Manley
created: 2026-10-29
diataxis: reference
tracker: hb-w4h
---

# SOLID and Clean Architecture standard

This standard governs every project under the Workspace: all new code, and any existing code a
change touches. It does not require retrofits; an existing module is brought into line only where a
diff already changes it, and a project's current layout is not a violation in itself. `/deliver`
reads this file as the binding `constitution`, and reviewers measure diffs against the
[Reviewer checklist](#reviewer-checklist) at the end.

## 1. The dependency rule

Code sits in four rings, and imports point inward only: domain <- application <- adapters <-
entrypoints.

- **Domain**: types and rules of the problem itself; pure, no IO, no framework imports.
- **Application**: use cases that orchestrate domain code and reach IO only through ports it
  receives as arguments.
- **Adapters**: the code that touches the outside world (filesystem, process, network, database,
  clock, randomness, hardware) and implements the ports the application declares.
- **Entrypoints**: CLIs, hooks, daemons and servers; they construct the adapters, wire them into
  the application, and contain no rules of their own.

An inner ring never imports an outer one. A domain module importing `subprocess`, `fs`, `reqwest`
or an adapter module is a violation regardless of how small the call is.

| Ring | Python | Rust | TypeScript | PowerShell |
|---|---|---|---|---|
| Domain | `<pkg>.domain` subpackage, or `domain_*.py` modules in a flat package | `domain` module of a pure `core` crate | `src/domain/` | pure functions in a `.psm1` module, no IO cmdlets |
| Application | `<pkg>.app` subpackage, or `app_*.py` modules | `app` module of the `core` crate | `src/app/` | `.psm1` functions that take IO as parameters |
| Adapters | `<pkg>.adapters` subpackage, or `adapter_*.py` modules | `adapters` module of the entry crate, or its own crate | `src/adapters/` | `.psm1` functions that call IO cmdlets (`Get-Content`, `Invoke-RestMethod`, `Start-Process`) |
| Entrypoints | `<pkg>.cli` (or `__main__.py`, hook scripts) | `main.rs` of a binary crate | `src/<entry>.ts` | `.ps1` entrypoint scripts that import the modules |

## 2. Earned abstraction

*A protocol, trait, or interface is introduced only at a boundary where the dependency is IO (process, network, filesystem, database, clock, randomness, hardware) or where a second real implementation exists. A test double counts as a second implementation only for IO. Pure in-process code with one implementation is called directly.*

`AGENTS.md` says to avoid premature abstractions and hypothetical future-proofing; this rule is that
instruction made decidable, not an exception to it. An interface at an IO boundary is earned now
(it is what lets the application be tested without the outside world), and every other interface
waits until a second real implementation exists.

## 3. SOLID, as practised here

**Single responsibility.** A module has one reason to change: one rule set, one IO boundary, or one
entrypoint's wiring. A module that both parses a file format and decides what to do with the
result has two, and splits along that line when a diff touches it.

**Open/closed via registries.** New variants are added by registering them, not by editing a
dispatch. `System.Control/src/system_control/effects/registry.py` maps effect names to factories
through `register_effect`, and aether's `LLMProvider` (`Roleplaying/src/llm/provider.ts`) lets a new
model backend ship without touching its callers. A growing `if`/`match` on a type tag is the signal
to reach for a registry, once there are real variants to register.

**Liskov substitution via conformance assertions.** Every implementation of a protocol carries a
module-level assertion that the type checker verifies, as System.Control's device drivers do with
`_: type[Device] = MyDevice` (for example `devices/govee_lan.py`). An implementation that cannot
satisfy the assertion without suppressing the type checker does not substitute and is not an
implementation.

**Interface segregation via narrow protocols.** A port exposes only the operations its consumers
call. aether's `WorldMapStore` (`Roleplaying/src/world-map/store.ts`) is the world-map surface the
engine needs, not the database client behind it. A consumer that implements stubs for methods it
never calls is a sign the port is too wide.

**Dependency inversion via ports composed at the entrypoint.** IO sits behind ports, and the
entrypoint constructs the concrete adapters and passes them in. aether's `DungeonMaster(deps)`
(`Roleplaying/src/dm.ts`) receives its `llm`, `bridge` and `memory` collaborators through a `deps`
object rather than instantiating them. Domain and application code never call a constructor for an
adapter.

## 4. Clean code rules already in force

- Public APIs are typed: Python type hints checked by mypy, TypeScript without `any` at exported
  boundaries, PowerShell `[Parameter()]` with declared types.
- Public functions, classes and modules carry substantive docstrings that state intent and
  contract, not a restatement of the name.
- Tests live in sibling test files, never inline in an implementation file. Rust declares
  `#[cfg(test)] mod tests;` in `foo.rs` with the tests in `foo/tests.rs`; Python, TypeScript and
  PowerShell use their `tests/` trees.
- Tests follow the test pyramid as defined in the Workspace
  [Testing strategy](../../CLAUDE.md) section ("Testing strategy (all projects under Workspace/)").
- No error handling, fallbacks or validation for cases that cannot happen; internal code and
  framework guarantees are trusted.
- Validation happens only at system boundaries: user input, files, network responses, process
  output, hook stdin.

## 5. Reuse rule

- **Rule of Three.** A utility needed by a third project moves to the shared library, `gm-common`,
  and the existing copies are replaced by imports.
- **Never copy a utility from another project.** If a second project needs it, import it from
  `gm-common` if it is there; otherwise write it locally and leave the Rule of Three to trigger the
  move.
- **Vendoring only where packaging isolation forces it** (a consumer that cannot declare a
  dependency on the shared package). A vendored copy carries a byte-identity check against its
  canonical source that fails CI on drift; `claude-marketplace/ci/check-vendored-sync.py` is the
  pattern.

## 6. Reference layouts

These layouts are mandatory for new projects and the template; descriptive for existing ones.

Python:

```text
src/<pkg>/domain/      pure types and rules
src/<pkg>/app/         use cases; IO only through ports passed in
src/<pkg>/adapters/    filesystem, process, network, hardware
src/<pkg>/cli/         entrypoint; constructs adapters and wires them
tests/                 unit/ and integration/, mirroring src/<pkg>/
```

Rust:

```text
crates/core/                 pure domain + application, no IO dependencies
crates/core/src/foo.rs       declares #[cfg(test)] mod tests;
crates/core/src/foo/tests.rs tests for foo.rs
crates/<entry>/              binary: adapters + composition in main.rs
```

TypeScript:

```text
src/domain/            pure types and rules
src/app/               use cases; IO only through ports passed in
src/adapters/          fs, process, network, database
src/<entry>.ts         entrypoint; constructs adapters and wires them
tests/{unit,integration,contract}/
```

PowerShell:

```text
lib/*.psm1             functions; no top-level side effects
*.ps1                  entrypoint scripts; import lib/ and perform the wiring
tests/*.Tests.ps1      Pester tests for lib/
```

## Reviewer checklist

These five items are the `## Checklist` of the `review:architecture-conformance` persona in the garrettmanley marketplace; edit both or neither.

1. Dependency direction: does every new or changed import point inward (domain <- application <- adapters <- entrypoints)? Name the offending import.
2. Earned abstraction: is every new protocol, trait, or interface at an IO boundary or backed by a second real implementation? Name any that is neither.
3. Test placement: is every test in a sibling test file, never inline in an implementation file?
4. Shared-library duplication: does the diff add a utility (e.g. UTF-8 forcing, atomic write, frontmatter parsing) that a shared library or the same repo already provides? Name the existing symbol.
5. Composition at the entrypoint: are IO adapters constructed in the entrypoint (CLI, hook, daemon, server) and passed in, rather than instantiated inside domain or application code?
