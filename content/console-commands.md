# Scene Director Console Commands

This file lists all console commands registered by the Scene Director plugin.

## 1) `RunSceneDirector`

Runs an Action Graph by partial name (for the sake of simplicity).

Syntax:

- `RunSceneDirector <NamePart>`
- `RunSceneDirector <NamePart1> <NamePart2> ...`

Example:

- `RunSceneDirector Intro`

---

## 2) `scenedirector.debug`

Toggles overview HUD for active graphs and average task tick time.

Syntax:

- `scenedirector.debug` (toggle)
- `scenedirector.debug 1`
- `scenedirector.debug 0`

What it shows:

- number of active graphs;
- number of active tasks;
- number of unique participants;
- `Task tick average` table by task class.

---

## 3) `scenedirector.debugnode`

Draws 3D text above participants with currently active Scene Director tasks.

Syntax:

- `scenedirector.debugnode` (enable for all)
- `scenedirector.debugnode 0`
- `scenedirector.debugnode <Tag1> <Tag2> ...` (enable with tag filter)

Examples:

- `scenedirector.debugnode`
- `scenedirector.debugnode NPC_A`

Limitations:

- drawing happens in game viewport (PIE/Play);
- no drawing on dedicated server;
- if there are no active tasks, labels will not appear.

---

## 4) `scenedirector.debugnode.cleartags`

Clears tag filter for `scenedirector.debugnode`.

Syntax:

- `scenedirector.debugnode.cleartags`

After execution:

- tag-based filtering is disabled;
- all participants are shown again (if `scenedirector.debugnode` is enabled).

---

## 5) Graph Trace (Editor UI)

Use it when you want to understand how the graph is running at runtime: which nodes were activated, what path was taken, and where execution stopped or failed.

Graph Trace is shown directly in the Action Graph editor.

- Open the graph asset.
- Turn on **Toggle Graph Trace** in the toolbar, or press `T`.
- Watch runtime events in the **Trace** tab.
- Trace data is temporary and is cleared after editor restart.

Trace includes node activations, route hops (including portals), task failures, abort/finish lifecycle events, and **state restore** after load.
