# Feature Matrix / Comparison

This page helps you position Scene Director against common Unreal workflows.

## Scope reminder

Scene Director is a **scene orchestration and scripting layer**.

- It is not a replacement for autonomous AI decision systems.
- It is strongest when you need deterministic multi-actor flow.

---

## Comparison by workflow type

## 1) Scene Director vs ad-hoc Blueprint scripting

Best fit:

- **Scene Director**: reusable, large, multi-actor scripted flows.
- **Ad-hoc BP scripts**: tiny one-off interactions.

Where Scene Director is stronger:

- visual flow readability at scale (nested graphs, macros, portals);
- explicit input/output routing instead of implicit graph spaghetti;
- reusable modular scene blocks with parameters;
- built-in runtime debugging and scene-level control.

Where ad-hoc BP can still be enough:

- quick prototype logic that will not be reused;
- very small local interactions in a single actor BP.

## 2) Scene Director vs Behavior Trees / StateTree (AI brain layer)

Best fit:

- **Scene Director**: directed scripted sequences and actor coordination.
- **BT/StateTree**: continuous autonomous decision making.

Where Scene Director is stronger:

- deterministic scripted staging (who does what and when);
- narrative/encounter flow with explicit phase transitions;
- easier authoring of cross-actor synchronization in one place.

Where BT/StateTree is stronger:

- reactive long-running AI behavior loops;
- utility/goal-based decision logic;
- navigation/combat decision policies over time.

Recommended in production:

- use BT/StateTree for "what NPC wants",
- use Scene Director for "how this scripted moment unfolds".

## 3) Scene Director vs Sequencer

Best fit:

- **Scene Director**: gameplay-driven logic and interactive branching scenes.
- **Sequencer**: timeline-driven cinematic playback and camera choreography.

Where Scene Director is stronger:

- runtime branching based on gameplay conditions;
- participant binding and parameterized starts;
- easy connection to gameplay nodes (move, rotate, trigger, wait/follow style beats).

Where Sequencer is stronger:

- authored camera cuts and keyframed animation tracks;
- polished linear cinematic timing.

Recommended in production:

- Scene Director can orchestrate logic around a Sequencer moment,
- Sequencer can handle pure cinematic timeline sections.

## 4) Scene Director vs level-only trigger logic

Best fit:

- **Scene Director**: structured scene logic with reusable flow modules.
- **Trigger-only logic**: very small local start conditions.

Where Scene Director is stronger:

- keeps orchestration out of scattered level BP scripts;
- easier maintenance for larger quest/encounter logic;
- better testability and reuse across maps.

Where trigger-only can be enough:

- single overlap -> single immediate action patterns.

---

## Feature checklist (practical)

Scene Director currently provides:

- node-based orchestration for multi-actor scripted flow;
- nested graphs and parameterized modules;
- runtime participant binding and launch-time parameters;
- Blueprint + C++ custom Action Node authoring;
- world authoring helpers (`ActionAnchor`, `ActionRoute`, `ActionTriggerVolume`);
- state persistence hooks and save integration paths;
- runtime debug overlays and console command tooling.

---

## Decision guide

Choose Scene Director first when:

- your scripted interactions span multiple actors;
- Blueprint logic is becoming hard to read/maintain;
- you need deterministic branching scene flow;
- you want reusable scene modules instead of one-off scripts.

Keep it lightweight (or use other tools) when:

- interaction is tiny and truly one-off;
- you need autonomous AI reasoning rather than scripted orchestration;
- requirement is only linear cinematic timeline playback (where plain Sequencer is enough).

Note:

- Scene Director and Sequencer are complementary.
- A common setup is Sequencer for camera/timeline, Scene Director for gameplay orchestration, branching, and actor coordination around that timeline.

---

## Positioning one-liner

**Scene Director sits between raw Blueprint scripting and autonomous AI systems: a production-oriented orchestration layer for directed, readable, reusable gameplay scenes.**
