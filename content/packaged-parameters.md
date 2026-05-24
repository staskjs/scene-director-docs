# Packaged Parameter Serialization Notes

## What was actually broken

In packaged builds, Unreal was crashing while loading Scene Director graph CDOs with a stack like:

- `FUnversionedPropertySerializer::SerializeAsInteger()`
- `SerializeUnversionedProperties()`
- `UScriptStruct::SerializeItem()`
- `FArrayProperty::SerializeItem()`

The crash was caused by storing editor-facing parameter metadata directly inside cooked runtime assets.

In plain language:

> - the editor needed rich parameter data (`FInstancedPropertyBag`, `FEdGraphPinType`)
> - packaged builds tried to deserialize arrays of structs containing that data
> - Unreal's unversioned property serializer did not handle that layout safely for these assets
> - result: packaged game crashed before map load finished
>
> ## Why some earlier attempts half-worked

Marking nested graph overrides as editor-only removed the crash, but it also removed the data needed by nested parameterized graphs at runtime. That is why root graphs started working while nested graphs lost their parameter values.

## Final fix

The working approach is:

1. Keep authoring-only parameter data editor-only.
2. Before save/cook, convert it into a simpler cooked-safe representation.
3. In runtime, reconstruct the runtime parameter value from that simplified representation.

That is what the code now does:

- `InputParameters` stays under `WITH_EDITORONLY_DATA`
- nested `ParameterOverrides` stay under `WITH_EDITORONLY_DATA`
- `USceneDirector::PreSave(...)` builds `CompiledInputParameterValues`
- `UActionNode_RunActionGraph::PreSave(...)` builds `SerializedParameterOverrides`
- runtime reconstructs `FSceneDirectorParameterValue` from those cooked-safe arrays

## Important detail

It was not enough to remove `FInstancedPropertyBag`.

An intermediate version still crashed because the cooked-safe struct still contained `FEdGraphPinType`, which itself was too heavy/problematic for this serialized path.

So the final cooked-safe format uses only simple fields:

- parameter id
- pin category/subcategory names
- referenced type object
- container kind
- serialized literal value as string

## Rule for future changes

If a Scene Director parameter field exists only to support authoring/UI/editor introspection, do not put that rich reflected type directly into cooked CDO arrays.

Instead:

- keep the rich source data editor-only
- generate a small runtime DTO in `PreSave`
- rebuild the runtime object from that DTO after load

