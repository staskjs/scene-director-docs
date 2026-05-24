# Scene Director FAQ

## Does this replace my NPC AI?
No. It runs scripted scenes — who does what and when. Your AI still decides what the NPC wants to do.

## I already use Sequencer. Why add this?
Sequencer is great for cameras and timelines. Scene Director handles branching gameplay: who moves where, when a scene starts, what happens next.

## Do I need C++?
No. You can build and run graphs in Blueprint. C++ is only if you want custom task nodes or deeper integration.

## Will I have to rebuild my game around it?
No. Plug it in step by step and call it from your existing Blueprint or C++ code.

## Is it only for story games?
No. Cutscenes, patrols, ambient moments, combat setup, shop interactions — anything with a clear sequence of steps.

## Can I see what the graph is doing at runtime?
Yes. Console commands, debug overlays, and graph trace in the editor help you follow active tasks.

## Does it work with save/load?
Yes. Graph progress can be saved and restored so a scene can continue after load instead of restarting from scratch.

## Must I use the built-in anchors, routes, and nodes?
No. They are shortcuts. You can use your own actors, tags, and custom nodes.

## Am I locked into this plugin?
Mostly no. Graphs are plain assets in your project. You extend behavior with your own nodes — nothing hidden in a black box.

## How do I know if it fits my project?
Rebuild one real interaction you already have (two NPCs, a trigger, a short sequence). If the graph is easier to read and change than your current setup, it is a good fit.
