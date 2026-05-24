# Participant Schema and Resolver

Use this when your project identifies NPCs/actors not by simple actor tags, but through your own systems.

Typical examples:

- gameplay tags
- data assets/descriptors
- internal registries/managers
- custom search rules
- optimization needs (avoid broad world scan by plain tags)

Goal: designers keep filling `Participant Entries`, and runtime finds correct actors using your project logic.

## Why customize

There are two separate tasks:

1. **How participants are described in the graph**
  (`USceneDirectorParticipantSchema`)
2. **How actors are found in the world at runtime**
  (`USceneDirectorParticipantResolver`)

If your project has custom participant logic, you usually need both.

---

## 1) Create your entry struct

This struct is what designers edit in `Participant Entries`.

Example:

```cpp
USTRUCT(BlueprintType)
struct FMySceneParticipantEntry
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SceneDirector")
    FName ParticipantTag = NAME_None;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SceneDirector")
    FString DisplayLabel;
};
```

Use any fields that are natural for your project (tags, data asset refs, ids, etc.).

---

## 2) Create your schema class

This class says:

- what fields are shown in `Participant Entries`,
- how to get participant id from those fields,
- what text is shown in the participant row.

Code example:

```cpp
UCLASS()
class UMySceneDirectorParticipantSchema : public USceneDirectorParticipantSchema
{
    GENERATED_BODY()

public:
    // Which USTRUCT is stored in each participant row (Details panel + InstancedStruct in records).
    virtual UScriptStruct* GetEntryStruct() const override
    {
        return FMySceneParticipantEntry::StaticStruct();
    }

    // Maps one edited row into the runtime slot: ParticipantId (resolve key), Label (display hint).
    // Return false if the entry is incomplete -- runtime treats it as "no slot" until fixed.
    virtual bool TryBuildSlot(const FInstancedStruct& Entry, FSceneDirectorParticipantSlot& OutSlot) const override
    {
        const FMySceneParticipantEntry* Typed = Entry.GetPtr<FMySceneParticipantEntry>();
        if (!Typed || !Typed->Descriptor)
        {
            return false;
        }

        OutSlot = FSceneDirectorParticipantSlot();
        OutSlot.ParticipantId = Typed->Descriptor->ParticipantTag;
        OutSlot.Label = Typed->Descriptor->DisplayLabel.ToString();
        return !OutSlot.ParticipantId.IsNone();
    }

    // Per-row title in the Participant Entries array (and anywhere a short row label is shown).
    virtual FText GetEntryDisplayText(const FInstancedStruct& Entry) const override
    {
        const FMySceneParticipantEntry* Typed = Entry.GetPtr<FMySceneParticipantEntry>();
        if (!Typed || !Typed->Descriptor)
        {
            return FText::FromString(TEXT("<empty>"));
        }

        if (!Typed->Descriptor->DisplayLabel.IsEmpty())
        {
            return Typed->Descriptor->DisplayLabel;
        }

        return FText::FromName(Typed->Descriptor->ParticipantTag);
    }
};
```

---

## 3) Create your resolver

This class contains your actor lookup logic at runtime.

Use it when actor lookup should be based on gameplay tags, data assets, registries, or any custom rule.

Code example (Gameplay Tags):

```cpp
UCLASS()
class UMyGameplayTagParticipantResolver : public USceneDirectorParticipantResolver
{
    GENERATED_BODY()

public:
    virtual bool TryFindActorForSlot(UWorld* World, const FSceneDirectorParticipantSlot& Slot,
                                     AActor*& OutActor) const override
    {
        OutActor = nullptr;
        if (!World || Slot.ParticipantId.IsNone())
        {
            return false;
        }

        FGameplayTag Tag = FGameplayTag::RequestGameplayTag(Slot.ParticipantId, /*ErrorIfNotFound=*/false);
        if (!Tag.IsValid())
        {
            return false;
        }

        for (TActorIterator<AActor> It(World); It; ++It)
        {
            AActor* Actor = *It;
            if (!IsValid(Actor))
            {
                continue;
            }
            if (const IGameplayTagAssetInterface* Tagged = Cast<IGameplayTagAssetInterface>(Actor))
            {
                if (Tagged->HasMatchingGameplayTag(Tag))
                {
                    OutActor = Actor;
                    return true;
                }
            }
        }
        return false;
    }
};
```

## 4) Assign classes in Project Settings

Open **Project Settings → Plugins → Scene Director**.

- **Participant Schema Class** — your schema class.
- **Participant Resolver Class** — your resolver class.
- **Priority Conflict Policy** — when a new root launch **shares a participant actor** with an already running root graph and both have the **same priority**:
  - **Incoming Wins On Equal** (default) — the new launch stops the active graph.
  - **Active Wins On Equal** — the new launch is rejected.

Priority values themselves are set per graph asset (**Priority** on the Action Graph). See [Runtime Control — Priority conflicts](./runtime-control.md#priority-conflicts-between-root-graphs).

---

## 5) Use in Action Graph

- Open your Action Graph.
- In **Participant Entries**, fill rows with your custom fields.
- Run graph: Scene Director will find actors using your resolver.

---

## 6) Runtime order (per slot)

1. Scene Director reads participant data from graph entries (through schema).
2. When it needs a real actor in the level, it asks your resolver.
3. If resolver finds actor, task runs on that actor.
4. If not, task that needs this participant fails.

