# Runtime Control

This guide covers how to stop graphs, check whether an actor is busy, and what happens when you try to start the same graph again.

For launch basics, see [Basic Usage](./getting-started.md). For persistence details, see [State Persistence](./state-persistence.md).

## Stop a running graph

Most stop functions live on **Scene Director Subsystem**.

All of them accept an optional **`Clear Persisted State`** flag (advanced). When enabled, stopped runs also delete their in-memory persistence snapshot for that graph.

### Stop everything

- `StopAllSceneDirectors(Clear Persisted State)` — stops all active runs in this world. Call on **Scene Director Subsystem** (use **Get Scene Director Subsystem** when you only have a world context).

### Stop by actor

Use these when the graph runs in **Single Runtime Participant** mode and you know which actor should stop.

- `StopSceneDirectorsForActor(Actor, Clear Persisted State)` — stops every active run bound to that actor.
- `StopSceneDirectorsForActorByClass(Actor, Graph Class, Clear Persisted State)` — same, but only for one graph class.

Typical use: the player leaves an area and you want to cancel that NPC's personal behavior graph.

### Stop by graph class

- `StopSceneDirectorsByClass(Graph Class, Clear Persisted State)` — stops all active instances of one Action Graph, no matter which actors they use.

### Stop from inside a graph

- **`Stop Other Graphs`** — stops every other active run that shares the same single-runtime participant as this node. The current run keeps going. See [Action Graph Toolkit](./graph-toolkit.md#stop-other-graphs).
- **`Abort`** — hard-stops the current run. See [Abort](./graph-toolkit.md#abort).

---

## Check whether an actor is busy

- `IsActorInRunningScene(Actor)` returns `true` when the actor is a bound participant in any **currently running** Scene Director instance, including nested child graphs.

Useful before starting a new AI state, opening a dialog, or launching another graph on the same character.

---

## Starting the same graph again

Behavior depends on graph mode.

### Normal participant-slot graphs

If the same graph class is **already running**, a second `Run Scene Director` call is **ignored** and returns `false`.

Exception: if that run is in **Pause Gracefully** mode, a new launch **cancels the pause request** and returns the existing instance instead of starting a duplicate.

### Single Runtime Participant graphs

Parallel runs of the **same graph class** are allowed when each run uses a **different actor**.

Example: ten NPCs can all run the same "Idle Behavior" graph at once — one instance per actor.

---

## Priority conflicts between root graphs

Many root Scene Director graphs can run **at the same time**. Priority is checked **only when the new launch shares at least one participant actor** with an already running root graph.

Examples:

- A shop scene on `ShopKeeper` and a patrol scene on `GuardA` can run in parallel — no shared actors, no conflict.
- A new cutscene and an idle loop both bound to the same NPC **do** conflict — Scene Director compares **Priority** on the graph assets.

When there is a shared participant actor:

- Higher priority wins and can stop lower-priority conflicting runs.
- If priorities are equal, the result depends on **Project Settings → Plugins → Scene Director → Priority Conflict Policy**:
  - **Incoming Wins On Equal** (default) — the new graph stops the active one.
  - **Active Wins On Equal** — the new launch is rejected.

If the winning graph has **Clear Preempted Graph State** enabled, stopped lower-priority runs also lose their persisted in-memory snapshot.

Notes:

- Priority applies to **root** launches through `Run Scene Director`.
- Child graphs started by **`Run Action Graph`** do not participate in this priority logic.

See also [Graph settings](./getting-started.md#graph-settings).

---

## Restore flag on launch

Both launch functions accept **`Restore From State`** (advanced, default `true`):

- `Run Scene Director(..., Restore From State)`
- `Run Scene Director With Single Actor(..., Restore From State)`

When `true` and persistence is enabled on the graph, Scene Director tries to resume from the in-memory snapshot before starting fresh.

Set `false` when you intentionally want a clean run even though old state still exists.
