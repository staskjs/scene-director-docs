# Built-in nodes

A quick reference for the nodes you get out of the box.

For graph structure (macros, portals, nested graphs), see [Graph toolkit](./graph-toolkit.md). For custom tasks, see [Custom nodes](./custom-nodes.md).

## Movement

- **Move To Anchor** — pathfind a participant to an `ActionAnchor`.
- **Move To Route Point** — go to one point on an `ActionRoute`.
- **Move Along Route** — walk the full route spline.
- **Teleport To Anchor** — instant move to an anchor.
- **Teleport To Nearest NavMesh** — unstuck: snap to nearby walkable navmesh.
- **Follow Player** — keep following the player until stopped or failed.
- **Follow Actor** — follow another actor (by tag) with pathfinding.

## Rotation

- **Rotate To Anchor** — turn a participant to face an anchor.
- **Rotate To Route Point** — turn to face a point on a route.
- **Rotate To Player** — turn a participant toward the player.
- **Rotate Player To Anchor** — turn the player to face an anchor.

## Animation

- **Play Animation** — play a montage or animation asset on a participant.
- **Stop Animation** — stop the current montage or animation.

## Player

- **Wait For Player Proximity** — continue when the player enters a radius.
- **Set Player Invulnerability** — turn damage immunity on or off during a scene.
- **Set Collision Ignore With Players** — ignore collision between this actor and players.
- **Teleport Player To Anchor** — move the player to a marked spot.

## Actor & proximity

- **Wait For Actor Proximity** — continue when another actor enters a radius.

## Spawn & attach

- **Spawn Actor At Location** — spawn a prop or helper at a world transform.
- **Spawn Actor Attached** — spawn something attached to a participant socket.
- **Attach Actor** — attach an existing actor to a participant socket.
- **Detach Actor** — detach from parent and optionally simulate physics.
- **Destroy Actors (by Tag)** — clean up temp actors spawned for the scene.
- **Spawn Niagara At Anchor** — play a VFX at an anchor.
- **Deactivate Niagara (by Tag)** — stop or destroy Niagara systems by tag.
- **Play Sound At Anchor** — play audio at an anchor location.
- **Stop Sound** — stop a sound started earlier in the graph.

## Flow

- **Branch** — pick `True` or `False` from a bool condition.
- **Wait (Seconds)** — simple delay before the next step.
- **Gate** — block or pass flow until you open or close the gate.
- **Sequence** — cycle through numbered outputs in order on each pulse.
- **For Each (Count)** — repeat a branch a fixed number of times.
- **Random** — pick a weighted random branch (dialogue variants, idle quirks).
- **Pass Through** — merge or reroute exec lines without extra logic.
- **Log** — print a debug message when flow passes through.

## See also

- [World helpers](./world-helpers.md) — anchors, routes, trigger volumes in the level.
- [Graph toolkit](./graph-toolkit.md) — macros, portals, pause, abort, nested graphs.
