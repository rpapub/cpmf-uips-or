# Known Problems and Edge Cases

## Design Philosophy

**cpmf-uisor modifies `.content` files only.** Hash computation, variable declarations, and workflow synchronization are UiPath Studio's responsibility.

After using cpmf-uisor, the user must open the project in Studio to finalize changes. Studio will:
- Regenerate ContentHash values
- Manage `ObjectRepositoryVariableData` declarations
- Sync workflow XAML copies when objects are re-added

This is by design — these are undocumented UiPath internals that would be fragile to implement externally.

---

## Architecture Discovery

### Workflow XAML Embeds Object Repository Data

When an Object Repository item is used in a workflow, UiPath Studio **embeds a copy** of the TargetApp/TargetAnchorable into the `.xaml` file.

```
.objects/.content  ──(copy at drag-drop)──>  workflow.xaml
```

- Workflows execute independently of `.objects/` folder
- Renaming/deleting `.objects/` folder doesn't break execution
- Only affects Object Repository UI navigation

**Implication**: External modifications to `.objects/` do NOT automatically update existing workflow usages.

---

## Variable Syntax

### GUI vs File Format

UiPath uses **different syntaxes** for the Studio GUI and the `.content` file format:

| Context | Syntax | Example |
|---------|--------|---------|
| **UiPath Studio GUI** | `{{varName}}` | Documented by UiPath |
| **`.content` files** | `[expression]` | Supports full VB.NET expressions |

Studio transforms between these formats. cpmf-uisor works with `.content` files directly.

### `.content` Expression Examples

**Simple (Screen URL):**
```xml
Url="[myUrl]"
```

**Complex (Element Selector with string.Format):**
```xml
ScopeSelectorArgument="[string.Format(&quot;&lt;wnd ... title='{0}' /&gt;&quot;, windowTitle)]"
```

### ObjectRepositoryVariableData

When using `[varName]` syntax, UiPath Studio adds variable declarations (for both Screen and Element):

```xml
<scg:List x:TypeArguments="ObjectRepositoryVariableData" x:Key="Variables" Capacity="1">
  <ObjectRepositoryVariableData DefaultValue="*" Name="myOtherUrl" />
</scg:List>
```

**cpmf-uisor manages these declarations** when parameterizing, including setting `DefaultValue`.

### Testing Observations

- Fresh parameterization (hardcoded → `[myUrl]`) works WITHOUT the Variables list
- Re-parameterization (`[myUrl]` → `[myOtherUrl]`) may require Studio intervention
- UiPath Studio adds the Variables list automatically when editing in the UI

### DataManager Variable Scope

When dragging a parameterized object into a workflow, UiPath Studio creates DataManager Variables with the `DefaultValue` from `ObjectRepositoryVariableData`. However:

- **Variables are created at narrow scope** (current sequence/activity level)
- **Manual adjustment required** to set scope to a higher level (e.g., workflow or project level)

This is a UiPath Studio limitation, not something cpmf-uisor can control.

---

## Object Repository Structure

### Hierarchy

```
Application
├── AppVersion (e.g., "1.0")
│   └── Screen (ObjectRepositoryScreenData, V2)
│       ├── Element (ObjectRepositoryElementData, V6)
│       │   └── Nested Element (child elements)
│       └── Element
└── AppVersion (e.g., "2.0")
    └── ...
```

- **Screen** = Application/window scope (maps to `NApplicationCard` at runtime)
- **Element** = UI element within that scope (maps to target selector)
- **Nesting**: Elements can contain child elements for complex UI hierarchies

### Screen Attributes (V2)

| Attribute | Purpose | Runtime Role | Parameterizable |
|-----------|---------|--------------|-----------------|
| `Url` | Browser URL / app path | Informational; **does not affect attachment** | Yes: `[varName]` |
| `Selector` | Window/browser identification | **Critical** — NApplicationCard attachment target | Yes: `[varName]` in attributes |

**Key insight**: `Url` parameterization alone doesn't enable cross-screen reuse. The `Selector` determines whether NApplicationCard can attach.

### Element Attributes (V6)

| Attribute | Purpose | Runtime Role | Parameterizable |
|-----------|---------|--------------|-----------------|
| `ScopeSelectorArgument` | Window scope context | Inherited from parent Screen; scopes element search | Yes: `[string.Format(...)]` |
| `FullSelectorArgument` | Primary element selector | **First** targeting method attempted | Yes: `[string.Format(...)]` |
| `FuzzySelectorArgument` | Relaxed matching rules | Fallback if strict selector fails | Yes: `[string.Format(...)]` |
| `ImageBase64` | Screenshot for image matching | Fallback targeting method | No |
| `CVScreenId` / `CvType` | Computer vision IDs | Fallback targeting method | No |

### SearchSteps — Targeting Strategy

The `SearchSteps` attribute defines the fallback order for element targeting:

| Value | Behavior |
|-------|----------|
| `"Selector"` | Selector only — no fallback |
| `"Selector, FuzzySelector"` | Strict selector, then fuzzy |
| `"Selector, FuzzySelector, Image"` | Adds image-based matching |
| `"Selector, FuzzySelector, Image, CV"` | Full fallback chain with computer vision |

```
Element Targeting Flow
─────────────────────────
FullSelectorArgument
    ↓ (if fails)
FuzzySelectorArgument
    ↓ (if fails)
ImageBase64 matching
    ↓ (if fails)
Computer Vision (CV)
```

### Why V2 Uses `[varName]` but V6 Uses `[string.Format(...)]`

The syntax difference reflects **where** the variable appears in the XML:

| Level | Attribute Example | Why This Syntax |
|-------|-------------------|-----------------|
| **Screen (V2)** | `Url="[myUrl]"` | Entire value is substituted → simple `[varName]` works |
| **Screen (V2)** | `title='[windowTitle]'` (in Selector) | Individual XML attribute value → simple `[varName]` works |
| **Element (V6)** | `ScopeSelectorArgument="[string.Format(&quot;&lt;wnd ... title='{0}'/&gt;&quot;, windowTitle)]"` | Variable goes **inside** an XML selector string → needs `string.Format` to build dynamically |

**Element selector structure:**
```xml
<!-- The selector itself is an XML string that needs dynamic value insertion -->
ScopeSelectorArgument="[string.Format(&quot;&lt;wnd app='chrome.exe' title='{0}'/&gt;&quot;, windowTitle)]"

<!-- At runtime, if windowTitle = "My Page", this becomes: -->
<!-- <wnd app='chrome.exe' title='My Page'/> -->
```

### Scope Inheritance

```
NApplicationCard (Screen.Selector → attaches to window)
    │
    └── Element (ScopeSelectorArgument → matches Screen.Selector)
            │
            └── Nested Element (ScopeSelectorArgument → inherits or overrides)
```

- **Element's ScopeSelectorArgument** typically mirrors the parent Screen's `Selector`
- When parameterizing Screen.Selector, corresponding Element.ScopeSelectorArgument should also be parameterized with the same variable
- Nested elements may define their own scope or inherit from parent

### Attribute Relationships

```
Screen.Selector ─────────────────┐
       │                         │
       │ (typically same value)  │
       ▼                         │
Element.ScopeSelectorArgument    │
       │                         │
       │ (scopes the search)     │
       ▼                         │
Element.FullSelectorArgument ◄───┘
       │                     (both need consistent
       │                      window reference)
       ▼
Element.FuzzySelectorArgument
```

When parameterizing for cross-screen reuse, ensure both Screen.Selector and Element.ScopeSelectorArgument use the same variable for the window title or identifier.

---

## Hash Management (Reference Only — Out of Scope)

This section documents UiPath internals for understanding. **cpmf-uisor does not compute or update hashes.**

### Two-Level ContentHash

Screen `.content` files have TWO ContentHash values:

```xml
<ObjectRepositoryScreenData ContentHash="GhY6fPzi10i-_bV1RnC1Aw" ...>
  <TargetApp ContentHash="LhWC8kj3Ck66J3g2pCZKtQ" ... />
</ObjectRepositoryScreenData>
```

- **Outer hash**: Changes when Variables list or structure changes
- **Inner hash**: Specific to TargetApp attributes

### Hash Algorithm (Unconfirmed)

- Format: 22 characters, Base64url encoded
- Likely: MD5 (128 bits = 16 bytes → 22 Base64 chars)
- Hash computed over content EXCLUDING the ContentHash attribute itself

### .hash File

- Located at `.data/ObjectRepositoryScreenData/.hash`
- Contains same value as ContentHash attribute
- Used for quick change detection without XML parsing

---

## Expression Compilation

### "Requires compilation" Error

```
Url Expression Activity type 'VisualBasicValue`1 (varName)' requires compilation in order to run.
```

Occurs when:
- Object Repository `.content` has `[varName]`
- But workflow XAML has stale embedded copy
- Or variable declaration missing from `.content`

### What Doesn't Fix It

- Deleting `.local/` folder
- Deleting `.hash` files
- Deleting compiled DLLs (`.local/install/*.dll`)
- Closing and reopening project

### What Does Fix It

- Editing the object in UiPath Studio (triggers hash recalculation)
- Deleting and re-adding object reference in workflow

---

## Scope

### What cpmf-uisor Does

- Reads `.content` files (inventory, audit)
- Modifies `.content` files (Url, Selector attributes)
- XML-escapes special characters
- Screen parameterization:
  - URL: `[varName]` syntax
  - Selector attributes: `[varName]` syntax
- Element parameterization:
  - ScopeSelectorArgument: `[string.Format("...", varName)]` syntax
  - FullSelectorArgument: `[string.Format("...", varName)]` syntax
- Manages `ObjectRepositoryVariableData` declarations:
  - Creates Variables list when parameterizing (with `DefaultValue`)
  - Removes variable from list on reset (parameterized → hardcoded)
  - Updates variable on rename (old → new)

### Out of Scope (By Design)

These are UiPath Studio's responsibility:

| Item | Reason |
|------|--------|
| ContentHash computation | Undocumented algorithm |
| `.hash` file updates | Studio regenerates |
| Workflow XAML sync | Requires Studio re-add |

### Expected User Workflow

After running `cpmf-uisor replace --apply`:
1. Object Repository `.content` is updated
2. Open project in UiPath Studio
3. Edit/save each modified object (triggers hash regeneration)
4. **Existing** workflow usages need manual refresh:
   - Delete object reference in workflow
   - Re-add from Object Repository

---

## Runtime Behavior

### NApplicationCard as Gatekeeper

The NApplicationCard must successfully **attach** before any elements inside can be accessed.

```
NApplicationCard attachment (TargetApp.Selector)
    ↓ must succeed first
Element targeting (ScopeSelectorArgument)
```

**Experiment results:**

| Scenario | Screen Selector | URL | InUiElement | Result |
|----------|-----------------|-----|-------------|--------|
| Matching screen | login ✓ | - | None | SUCCESS |
| Mismatched screen | order ✗ | - | None | **FAILS at NAppCard** |
| Mismatched + parameterized URL | order ✗ | ✓ | None | **FAILS at NAppCard** |
| Mismatched + UiElement passed | order ✗ | - | ✓ | SUCCESS |

**Key findings:**

1. **Selector determines attachment** - `TargetApp.Selector` must match current window for NApplicationCard to attach
2. **URL alone insufficient** - Parameterizing `Url` does NOT bypass Selector mismatch
3. **InUiElement bypasses Selector** - When `InUiElement` is set, `TargetApp.Selector` is ignored; attachment comes from passed UiElement
4. **Elements never attempted on failure** - If NApplicationCard fails to attach, elements inside are never accessed

### UiElement Session Pattern

When using `InUiElement`/`OutUiElement` properties:

```xml
<!-- Initialize.xaml - creates browser reference -->
<NApplicationCard OpenMode="IfNotOpen" OutUiElement="[BrowserVar]" ...>

<!-- Subsequent workflows - reuse browser reference -->
<NApplicationCard InUiElement="[BrowserVar]" OutUiElement="[BrowserVar]" ...>
```

- `InUiElement`: Attach to existing browser (bypasses TargetApp.Selector)
- `OutUiElement`: Output browser reference for downstream workflows
- UiPath warning: "Applications cannot be opened when using an input element"

### Implication for Parameterization

| Attribute | Can Parameterize | Runtime Effect |
|-----------|------------------|----------------|
| Screen.Url | Yes | Informational only if Selector mismatches |
| Screen.Selector | Yes | **Critical** for NAppCard attachment (without InUiElement) |
| Element.ScopeSelectorArgument | Yes | Only matters AFTER NAppCard attaches |

**Best practice**: Use `InUiElement` pattern to decouple Screen attachment from Selector matching.

---

## References

- [UiPath Docs: Creating an Object Repository - Variables in descriptors](https://docs.uipath.com/studio/standalone/latest/user-guide/creating-an-object-repository) — documents GUI syntax (`{{varName}}`)
- [Forum: Using variables in Object Repo UI Descriptors](https://forum.uipath.com/t/using-variables-in-object-repo-ui-descriptors/279239) — community discussion on file format
