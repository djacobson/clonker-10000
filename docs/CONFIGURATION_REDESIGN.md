# The Clonker 10000 — Configuration Redesign

**Proposed:** November 24, 2026  
**Origin:** Chapter 11  
**Target:** Chapter 12  
**Status:** Implemented — operational Config v5 baseline established  
**Original schema:** Config v4  
**Implemented schema:** Config v5  

> **Historical design record:** This document preserves the
> agreed Chapter 12 proposal. See Section 23 for implementation
> results and current sources of truth.

> Configure the device. Configure the intent.
> Let the adapter speak the protocol.

---

## 1. Motivation

The original Clonker configuration architecture has served
its initial Roku, Denon, and generic HTTP use cases well.

Device destinations are currently represented by endpoint
strings. Commands contain HTTP methods and paths, and
specialized adapter selection relies partly on recognition
of command signatures.

Chapter 11 experimentation with LG webOS demonstrated the
need to accommodate fundamentally different device protocols,
including persistent WebSockets, authenticated registration,
pairing, structured command payloads, and asynchronous
response processing.

Chapter 12 will establish a more explicit and extensible
device configuration architecture without sacrificing the
flexibility and simplicity of the original Clonker.

LG webOS is the first significant motivation for this
redesign. Future Apple TV, Fire TV, and other device
adapters may benefit from the same architectural foundation.

Keep It Simple.

## 2. Relationship to the LG webOS adapter

The standalone experimental adapter:

`firmware/clonker/devices/lg_webos.py`

is an intentional architectural reference for this redesign,
not abandoned experimental code.

It consolidates successful Chapter 11 laboratory experiments,
including:

- WebSocket transport and connection lifecycle.
- SSAP registration and request/response correlation.
- Separate pointer input connections.
- Cooperative receive processing.
- Pairing and client-key verification.
- Temporary development credentials.
- Transport and pairing diagnostics.

The associated laboratory scripts are located in:

`firmware/tests/test_lg_webos_*.py`

The adapter remains intentionally disconnected from
production device routing.

**LG runtime integration is deferred, but its configuration
requirements are not.**

Implement the LG device record, credential representation,
SSAP and pointer command formats, and associated editor
infrastructure during the configuration refactor.

The immediate operational objective is to regression-test
the redesigned configuration using existing supported devices
before connecting the LG adapter to the running application.

The final LG execution and asynchronous completion semantics
will be established through subsequent integration testing.

## 3. Design objectives

- Explicitly identify the type of each configured device.
- Separate device identity, role, type, endpoint, and commands.
- Select adapters by configured device type.
- Preserve editable fundamental and Custom Action commands.
- Support HTTP, SSAP, and pointer command representations.
- Accommodate device-specific configuration attributes.
- Provide a compact, protocol-aware configuration editor.
- Support adding and removing rooms through the editor.
- Automatically generate stable Custom Action IDs.
- Provide conditional pairing and credential controls.
- Preserve existing configuration persistence safeguards.
- Avoid unnecessary legacy schema compatibility.
- Preserve existing operational behavior through regression testing.
- Avoid speculative abstractions for future protocols.

## 4. Architectural invariants

The redesign must preserve the following principles:

- There remains one shared Dumb Queue™.
- Browser and physical controls use the same execution path.
- Fundamental actions retain their established identities.
- Custom Actions retain their ordered step semantics.
- Device adapters own protocol-specific behavior.
- The configuration layer owns configuration data and persistence.
- Display names are not internal identifiers.
- Blank destinations and fundamental commands remain valid
  intentional no-ops.
- No implicit fallback to another room or destination.
- No automatic command replay after transport failure.
- Configuration validity does not imply equipment reachability
  or successful command execution.
- Full configuration validation must not be repeated in
  latency-sensitive execution paths.

Do not introduce another action queue or an independent
execution path for a new protocol.

Outstanding protocol response metadata is not a command queue.

## 5. Device configuration model

### 5.1 Device identity and role

Retain the existing built-in destination identifiers:

| Device ID | Role |
|---|---|
| `device-1` | TV |
| `device-2` | AVR |
| `device-3` | Streaming |

These identifiers are independent of the device type.

For example, TV is a role, while LG webOS is a device type.

Do not infer device type from its role, endpoint port,
command syntax, or display label.

Future custom destinations remain outside the immediate
redesign scope.

### 5.2 Typed device records

Replace the existing endpoint-string representation with
structured device records.

Example Config v5 device fragment:

```json
{
  "devices": {
    "device-1": {
      "type": "generic-http",
      "endpoint": ""
    },
    "device-2": {
      "type": "denon",
      "endpoint": "192.168.50.40:8080"
    },
    "device-3": {
      "type": "roku",
      "endpoint": "192.168.50.28:8060"
    }
  }
}
```

Retain existing IPv4 and optional port syntax unless a
specific protocol requires an extension.

An unused device may be represented by a generic HTTP
device with a blank endpoint.

A separate `none` device type is unnecessary.

### 5.3 Device-specific attributes

Store device-specific configuration attributes directly
within the applicable device record.

Example LG webOS device:

```json
{
  "type": "lg-webos",
  "endpoint": "192.168.50.47:3000",
  "client_key": "PASTE_OR_PAIR_CLIENT_KEY_HERE"
}
```

The client key belongs to the configured device, not to
individual commands.

Avoid introducing a nested settings object unless future
requirements establish a genuine need for one.

Do not add unrelated authentication attributes to ordinary
Roku, Denon, or generic HTTP device records.

Device-specific attributes should be validated according
to the declared device type.

### 5.4 Adapter-owned attributes

Do not expose internal protocol machinery as user
configuration merely because a new protocol requires it.

Examples of adapter-owned responsibilities include:

- WebSocket connection paths and headers.
- Registration manifests.
- Protocol request identifiers.
- Connection and response timeouts.
- Persistent connection management.
- Authentication procedures.
- Receive buffers and outstanding response metadata.

The configuration describes the device and the commands
to execute. The adapter implements the protocol.

## 6. Room configuration

Retain the existing stable room identifiers:

- `room-1`
- `room-2`
- `room-3`

Support one to three configured rooms.

Only configured rooms should be represented in the
stored configuration.

Unused rooms do not require empty placeholder structures.

Removing a room must not renumber the remaining rooms.

### 6.1 Dynamic room editing

The configuration editor shall provide controls for adding
and removing rooms.

For an unconfigured room, display a compact Add Room
control instead of a complete empty configuration section.

Adding a room creates its default configuration structure
in the browser, including:

- Room name.
- Three built-in device records.
- Fourteen fundamental action definitions.
- An empty Custom Actions array.

Removing a room removes its entire configuration structure,
subject to user confirmation.

At least one configured room must remain.

Room additions and removals become persistent only after
a successful configuration save.

No additional firmware API endpoints or schema attributes
are required solely for this capability.

### 6.2 Benefits

Omitting unused rooms reduces:

- Stored configuration size.
- Runtime configuration memory consumption.
- Parsing and validation work.
- Configuration transfer and backup sizes.
- Unnecessary browser rendering.

It also makes focused configuration recipes practical,
including single-room experimental configurations.

## 7. Device-type registry

Establish a small centralized registry of device types.

| Type ID | Display label | Initial runtime status |
|---|---|---|
| `generic-http` | Generic HTTP | Operational |
| `denon` | Denon AVR | Operational |
| `roku` | Roku ECP | Operational |
| `lg-webos` | LG webOS | Integration pending |
| `apple-tv` | Apple TV | Planned |
| `fire-tv` | Amazon Fire TV | Planned |

Internal identifiers must remain independent of
user-facing labels.

The registry should provide the information needed for:

- Device type identification.
- User-facing display labels.
- Adapter selection.
- Supported command kinds.
- Device-specific attributes.
- Default endpoint ports, where applicable.
- Pairing capability.
- Implementation availability.

Avoid duplicating device-type knowledge independently
throughout the firmware and browser editor.

The registry should remain lightweight and avoid
unnecessary dependencies on transport implementations.

The exact registry structure and browser exposure
mechanism are implementation details.

### 7.1 Device-type availability

Experimental and planned device types may appear in
the configuration editor's device-type selector.

Types not yet operational must appear disabled
(greyed-out) in the normal editor.

Implement the LG configuration representation and
associated editor infrastructure during the refactor.

Enable normal LG device selection and execution at the
appropriate LG integration checkpoint.

Availability must be driven by the central registry
rather than independently hard-coded in the browser.

Device-type validation should reuse the central registry
and remain deliberately simple.

Do not introduce excessive validation machinery solely
to defend against manually modified configuration files.

## 8. Command configuration

### 8.1 Common command objects

Fundamental actions and Custom Action steps shall use
a common nested command representation.

Every command object shall contain an explicit `kind`
attribute.

Supported initial command kinds:

| Kind | Purpose | Command attributes |
|---|---|---|
| `http` | HTTP-oriented device commands | `method`, `path` |
| `ssap` | LG webOS SSAP requests | `uri`, optional `payload` |
| `pointer` | LG webOS pointer input | `button` |

The explicit command kind simplifies validation, editor
rendering, and adapter interpretation.

Do not infer command kinds from the presence or absence
of other attributes.

Only include attributes applicable to the command kind.

### 8.2 HTTP commands

Example Roku Home action:

```json
{
  "target": "device-3",
  "command": {
    "kind": "http",
    "method": "POST",
    "path": "/keypress/Home"
  }
}
```

Preserve editable GET and POST methods and command paths.

The HTTP command representation describes the configured
command, not necessarily its ultimate transport.

For example, the Denon adapter may recognize an eligible
volume command and execute it through its specialized
persistent TCP connection.

### 8.3 LG SSAP commands

Example LG volume command:

```json
{
  "target": "device-1",
  "command": {
    "kind": "ssap",
    "uri": "ssap://audio/volumeUp"
  }
}
```

Example command containing a structured payload:

```json
{
  "target": "device-1",
  "command": {
    "kind": "ssap",
    "uri": "ssap://system.launcher/launch",
    "payload": {
      "id": "com.webos.app.home"
    }
  }
}
```

The payload is an optional JSON object, not a string
containing encoded JSON.

The editor may present it as editable JSON text, but
must parse and validate it before saving.

Preserve the user's ability to experiment with arbitrary
SSAP URIs and applicable payloads.

Do not require a hard-coded library of every supported
LG command.

### 8.4 LG pointer commands

Example LG Home button command:

```json
{
  "target": "device-1",
  "command": {
    "kind": "pointer",
    "button": "HOME"
  }
}
```

Pointer input is distinct from SSAP request execution.

The LG adapter owns pointer connection acquisition,
message formatting, and transmission.

### 8.5 Toggle commands

Toggle actions shall contain independent ON and OFF
command objects.

Example LG mute toggle:

```json
{
  "target": "device-1",
  "on_command": {
    "kind": "ssap",
    "uri": "ssap://audio/setMute",
    "payload": {
      "mute": true
    }
  },
  "off_command": {
    "kind": "ssap",
    "uri": "ssap://audio/setMute",
    "payload": {
      "mute": false
    }
  }
}
```

This representation also permits independent HTTP methods
and paths without introducing special toggle-specific
protocol attributes.

Preserve the existing toggle history behavior for
operational devices.

### 8.6 Protocol request identifiers

An LG SSAP request transmitted by the adapter may resemble:

```json
{
  "id": "clonker-42",
  "type": "request",
  "uri": "ssap://audio/volumeUp"
}
```

The outer request ID is generated by the adapter for
response correlation.

It is not a user-editable configuration attribute.

An identifier inside a command payload may represent
application-specific data and legitimately be configurable.

Keep these meanings separate.

### 8.7 Blank commands

Preserve intentionally blank fundamental commands.

The exact empty representation for each command kind
must be defined consistently in the validator and editor.

An empty fundamental command is not a transport request.

Custom Action steps continue to require actual commands.

## 9. Custom Actions

### 9.1 Original design philosophy

Custom Actions were inspired by the flexibility of
iOS Shortcuts.

They intentionally allowed arbitrary HTTP GET and POST
commands rather than limiting the user to the predefined
fundamental action library.

Preserve that philosophy.

The introduction of LG webOS provides a genuine reason
to extend Custom Actions beyond generic HTTP.

### 9.2 Protocol-aware Custom Action steps

Custom Action steps shall use the same command objects
as fundamental actions.

Example mixed-protocol Custom Action:

```json
{
  "name": "Movie Mode",
  "id": "custom-action-1",
  "steps": [
    {
      "target": "device-1",
      "command": {
        "kind": "pointer",
        "button": "HOME"
      },
      "wait_after_ms": 1000
    },
    {
      "target": "device-3",
      "command": {
        "kind": "http",
        "method": "POST",
        "path": "/keypress/Home"
      },
      "wait_after_ms": 3000
    },
    {
      "target": "device-2",
      "command": {
        "kind": "http",
        "method": "GET",
        "path": "/goform/formiPhoneAppDirect.xml?MSQUICK1"
      },
      "wait_after_ms": 0
    }
  ]
}
```

This is an illustrative configuration fragment, not a
verified equipment automation recipe.

The target identifies the configured device.

The device type determines the applicable adapter and
supported command kinds.

Do not duplicate device type within each command step.

### 9.3 Execution semantics

Custom Actions shall execute through the appropriate
configured device adapters.

Preserve single-command semantics.

A Custom Action step must not implicitly initiate
physical button holds or repeat sequences.

Preserve existing Roku and Denon Custom Action behavior
during the initial regression phase.

Any changes to specialized transport optimization for
Custom Actions must be deliberate and tested.

### 9.4 Step delays

Preserve the existing completion-based delay semantics.

The current dispatcher begins `wait_after_ms` after
successful command transmission and returns the next
step to the Dumb Queue.

Other eligible commands may execute during the wait.

Do not change this established behavior speculatively.

The exact definition of successful completion for
asynchronous LG SSAP requests will be determined during
LG adapter integration.

## 10. Custom Action IDs

### 10.1 Automatic generation

Remove ordinary user editing of Custom Action IDs.

Generate an ID automatically when creating a Custom Action.

Display the ID in smaller, read-only text for diagnostic
and development purposes.

### 10.2 Identity rules

- Preserve the ID when renaming or editing an action.
- Preserve the ID when reordering actions.
- Generate a new ID when duplicating an action, if supported.
- Never derive identity solely from the display name.
- Never renumber existing actions merely because one is deleted.
- Validate imported IDs and reject invalid duplicates.
- Do not silently rewrite existing valid IDs.

Prefer generating new IDs that are unique throughout
the configuration.

Retain compatibility with existing valid room-scoped IDs.

The exact generation mechanism remains an implementation
detail and should avoid unnecessary dependencies.

### 10.3 Distinct identifier classes

| Identifier | Purpose |
|---|---|
| Room ID | Stable configured room |
| Device ID | Stable configured destination |
| Device type ID | Adapter and capability selection |
| Fundamental Action ID | Application-defined action |
| Custom Action ID | Stable user-defined action |
| Protocol request ID | Transient network correlation |

These identifiers have different scopes and lifetimes.

## 11. Configuration editor redesign

### 11.1 Compact device table

Replace the existing device address fields with a compact,
vertically organized table within each configured room.

| Role | Device type | IP address : port |
|---|---|---|
| TV | Type selector | Editable endpoint |
| AVR | Type selector | Editable endpoint |
| Streaming | Type selector | Editable endpoint |

The room name remains independently editable.

Device type selection may provide sensible default ports
for empty endpoints.

Never silently overwrite existing user-entered endpoints
or commands.

### 11.2 Conditional device-specific controls

When a selected device type requires pairing, display
a pairing button alongside an editable client-key field.

Both controls should be available together, allowing
the user to initiate pairing or manually enter an
existing client key.

Provide infrastructure for:

- Editable client-key entry.
- Pairing initiation.
- Pairing progress and result indication.
- Credential availability indication.

These controls should appear conditionally according
to the selected device type's declared capabilities.

Keep the layout compact for ordinary HTTP-oriented devices.

Implement the conditional editor infrastructure during
the configuration refactor.

Actual pairing operations remain deferred until the
existing-equipment regression checkpoint is complete.

### 11.3 Protocol-aware command editing

The selected destination's device type determines
the available command kinds and editor fields.

HTTP command editor:

- Method selector: GET or POST.
- Editable path.

SSAP command editor:

- Editable SSAP URI.
- Optional editable JSON payload.

Pointer command editor:

- Editable pointer button name.

Apply the same command editing principles to fundamental
actions, toggle commands, and Custom Action steps.

Custom Action steps additionally retain their existing
delay controls.

Changing a device type or command destination must not
silently discard or rewrite existing commands.

Identify incompatible commands clearly and allow the
user to resolve them.

### 11.4 Preserve existing editor capabilities

Retain:

- Room name editing.
- Fundamental action editing.
- Toggle ON/OFF command editing.
- Custom Action creation and editing.
- Ordered Custom Action steps and delays.
- Revision-aware saves.
- Configuration import and recipe browsing.
- Test Remote functionality.
- Existing save confirmation and error handling.

Add dynamic room creation and removal as described
in Section 6.

## 12. Explicit adapter selection

### 12.1 Execution flow

The configured target identifies a device record.

The device record explicitly identifies the device type.

The device type determines the adapter.

```text
Physical controls / Test Remote
              |
         Action dispatcher
              |
          Dumb Queue
              |
      Configured destination
              |
       Declared device type
              |
        device_adapters
              |
      Selected device adapter
              |
        Device transport
```

The dispatcher and adapter coordination layer should not
need to infer device identity from command syntax.

### 12.2 Protocol-specific transport decisions

Explicit adapter selection does not eliminate all
command-specific recognition.

It changes where that recognition belongs.

The Denon adapter may recognize volume commands eligible
for its specialized persistent TCP connection.

The Roku adapter may recognize commands eligible for
persistent HTTP, native held-button behavior, or other
specialized execution policies.

LG webOS distinguishes SSAP requests from pointer input.

These are adapter execution decisions, not device-type
discovery mechanisms.

Preserve the useful protocol-specific diagnostics and
transport behavior established in earlier chapters.

### 12.3 Adapter cache and lifecycle

Review and update the existing adapter cache,
configuration accessors, readiness checks, execution
delegation, cancellation, polling, and connection cleanup.

Changed configurations must not leave stale device-type
associations, endpoint associations, or authenticated
sessions active.

Credential changes may require session retirement even
when the endpoint remains unchanged.

Preserve existing changed-save and unchanged-save
semantics.

Do not reintroduce repeated full configuration validation
into latency-sensitive execution paths.

## 13. Deferred LG execution questions

The LG laboratory experiments demonstrated multiple
outstanding read-only SSAP requests with response
correlation.

They did not establish ordering guarantees for
state-changing commands or commands transmitted over
different WebSocket connections.

Future integration must distinguish:

- Command admission.
- Command transmission.
- Protocol acknowledgment.
- Actual equipment behavior.

The following questions are intentionally deferred until
the configuration refactor and existing-equipment
regression testing are complete:

- Whether SSAP Custom Action steps wait for acknowledgment
  before advancing.
- Ordering of state-changing SSAP requests.
- Ordering across SSAP and pointer connections.
- Asynchronous failure propagation.
- Response deadlines and timeout handling.
- Toggle advancement after asynchronous responses.
- Custom Action completion and delay timing for SSAP.
- Queue cancellation following delayed protocol failures.
- Exact unavailable-device execution semantics.

Resolve these questions through actual equipment testing
rather than speculative queue redesign.

The Config v5 schema does not depend on their resolution.

Do not introduce user-configurable acknowledgment policies,
response timeout attributes, or additional queues without
an established requirement.

## 14. Pairing architecture

Pairing is a device protocol operation.

The configuration interface orchestrates user interaction
and persists the resulting credentials.

The draft LG adapter already contains experimental pairing
helpers and client-key verification functionality.

Review and reuse those helpers rather than implementing
LG-specific WebSocket registration inside browser
management or configuration modules.

Conceptual pairing flow:

1. User selects a device requiring pairing.
2. Configuration UI requests a pairing operation.
3. The appropriate adapter initiates pairing.
4. The user approves the request on the equipment.
5. The adapter cooperatively processes the result.
6. The resulting credential is returned to the editor.
7. The user reviews and saves the updated configuration.

The approval wait must not block the main cooperative
scheduler for the entire human-interaction timeout.

Cancellation, rejection, timeout, and resource cleanup
must be handled explicitly.

Pairing success and configuration persistence are separate
operations.

Do not assume successful pairing means the resulting
credential has already been saved.

The operational pairing API and state model remain
deferred until LG integration.

### 14.1 Configuration validity versus device readiness

A valid configuration may contain:

- A blank endpoint.
- An intentionally blank fundamental command.
- A device awaiting pairing.
- A missing or placeholder credential.

Such configurations should remain importable and savable,
subject to the applicable device-type availability rules.

A device requiring authentication is not ready for
execution until its necessary credential is available.

An unready device must not prevent unrelated configured
devices from operating normally.

### 14.2 Credential handling

Actual client keys and authentication tokens must not be
committed to the public repository or published in recipes.

The maintainer may retain credentials privately and paste
them into the configuration editor as needed.

Do not include credentials in ordinary diagnostic snapshots,
Flight Recorder output, or error messages.

Review configuration API responses, browser presentation,
exports, and local backup files for credential exposure.

The existing management interface is trusted-LAN-only
and has no application-level authentication.

Masking a credential in the browser is not equivalent
to securing its storage or network transmission.

Revisit management-interface security before broadening
deployment beyond the existing trusted environment.

Temporary development credentials in the LG draft are
a laboratory convenience, not the permanent design.

## 15. Configuration size and resource considerations

### 15.1 Representative size measurements

During Chapter 12 design, the existing repository recipe:

`recipes/david-roku-denon-starter.json`

was converted in memory to the proposed Config v5
representation.

The experiment included typed device records, nested
command objects, explicit command kinds, and independent
toggle command objects.

No repository files were modified.

Measured minified JSON sizes:

| Configuration | Size |
|---|---:|
| Original Config v4, three rooms | 5,098 bytes |
| Proposed Config v5, three rooms | 7,022 bytes |
| Proposed Config v5, two configured rooms | 5,508 bytes |
| Proposed Config v5, Sunroom only | 2,610 bytes |

The complete three-room configuration increased by
1,924 bytes, approximately 37.7 percent.

The unused third room accounted for approximately
1.5 KB of the proposed Config v5 representation.

These measurements use the repository HTTP recipe,
not the latest live configuration, and do not include
LG credentials or SSAP payloads.

### 15.2 Avoid unnecessary JSON bloat

Prefer clear attribute names and consistent command
representations over abbreviated keys or clever compression.

Continue storing canonical minified JSON on the Pico.

Use readable, indented JSON for published recipes.

Omit unused rooms rather than retaining complete empty
room structures.

Include protocol-specific attributes only where applicable.

Do not store adapter-owned protocol machinery in
configuration records.

### 15.3 Proposed size limits

| Limit | Current | Proposed |
|---|---:|---:|
| Stored configuration | 8,192 bytes | 16,384 bytes |
| Incoming management HTTP request | 10,240 bytes | 18,432 bytes |

The proposed limits are provisional until verified through
Pico memory and configuration persistence testing.

Review actual request buffering, JSON parsing, validation,
canonical serialization, and save-time memory consumption.

Do not assume serialized JSON size directly represents
the runtime memory cost of its parsed object structure.

Retain existing room, Custom Action, step count, and
delay limits unless testing establishes a need to
change them.

## 16. Schema versioning and replacement

The current active schema is Config v4.

The incompatible redesign shall introduce Config v5.

There is no requirement to support legacy configuration
versions or automatic schema migration.

The Clonker currently has one development user who accepts
a controlled configuration replacement and temporary downtime.

Prepare a complete replacement configuration representing
the existing working installation.

Preserve externally:

- The current working configuration.
- Compatible firmware.
- Existing backup generations.

Do not assume old-schema backup files will validate under
the new firmware.

Use a deliberate deployment procedure with a compatible
firmware/configuration pair.

Preserve existing validation, canonical serialization,
revision checking, verified writes, backup rotation,
and recovery principles.

## 17. Configuration Recipe Library

The Configuration Recipe Library distributes complete
replacement configuration JSON files.

It should remain a simple publication and download
mechanism rather than becoming a protocol-aware
configuration service.

Update downloadable recipes and associated schema
version descriptions when Config v5 is introduced.

Review the recipe website, catalog, documentation,
and embedded configuration import functionality for
schema dependencies.

### 17.1 Publication workflow

The maintainer may provide an exported, working,
minified configuration JSON for recipe preparation.

The publication preparation process should:

1. Parse the working JSON.
2. Produce a readable, indented representation.
3. Preserve device types, commands, action IDs, Custom
   Action ordering, and step delays.
4. Replace sensitive credentials with descriptive placeholders.
5. Review other potentially sensitive values.
6. Validate the resulting JSON syntax and target schema.
7. Return the sanitized publication copy for review.

Example:

```json
{
  "type": "lg-webos",
  "endpoint": "192.168.50.47:3000",
  "client_key": "PASTE_OR_PAIR_CLIENT_KEY_HERE"
}
```

Never publish actual client keys, passwords, tokens,
or other authentication secrets.

Private LAN endpoints may be retained as intentional
recipe examples or replaced when requested.

The published recipe must not modify the maintainer's
working configuration.

### 17.2 Recipe import

The user should be able to import a recipe, review it,
edit device addresses and credentials, and explicitly save.

Placeholder credentials must be recognized as unavailable
credentials rather than transmitted to equipment as if
they were real authentication keys.

Pretty-printed recipe files may be larger than their
compact stored representation.

Review import size limits and canonicalization behavior.

### 17.3 Recipes as development tools

The existing recipe import mechanism also provides a
convenient way to switch between development configurations.

Maintain separate recipes for:

- Existing-equipment Config v5 regression testing.
- Subsequent LG webOS integration and experimentation.

The LG experimental recipe may replace Sunroom Denon
command mappings with LG commands and omit unrelated rooms.

The maintainer can restore the baseline configuration
by reimporting its recipe.

Switching between recipes also provides a useful test
of adapter cache invalidation and connection cleanup.

Do not introduce a separate development mode or
configuration profile manager solely for this purpose.

## 18. Application impact inventory

Inspect the current repository rather than relying solely
on historical documentation or conversation summaries.

Areas requiring review include:

- Configuration validation and normalization.
- Configuration accessors and active RAM state.
- Revision calculation and persistence.
- Startup loading and recovery.
- Device-type registry.
- Adapter cache construction.
- Device adapter selection and execution.
- Action dispatcher and Dumb Queue integration.
- Fundamental action and toggle handling.
- Custom Action admission and sequencing.
- Physical control coordination.
- OLED feedback and Custom Action selection.
- Configuration editor HTML and JavaScript.
- Management HTTP API.
- Test Remote page.
- Recipe browsing and JSON import.
- Repository examples and sample configurations.
- Diagnostic and Flight Recorder behavior.
- Existing standalone tests and regression procedures.

The current authoritative configuration implementation is:

`firmware/clonker/device_config_v2.py`

Its historical filename does not indicate the current
schema version.

The standalone LG draft must be included in this review
even though it is not yet a production configuration consumer.

Existing firmware laboratory and regression scripts are
located in:

`firmware/tests/`

These scripts are deployed to `/tests/` on the Pico.

Reuse relevant existing tests rather than unnecessarily
recreating previous experimental work.

## 19. Implementation sequence

### Phase 1 — Inventory and design

Inspect the current repository and working configuration.

Identify configuration consumers, adapter boundaries,
validation rules, UI dependencies, and test coverage.

Review the LG draft and laboratory findings.

Establish the Config v5 schema and document agreed
architectural decisions before cascading changes.

### Phase 2 — Configuration engine

Implement:

- Typed device records.
- Centralized device-type registry.
- Common command objects.
- HTTP, SSAP, and pointer command validation.
- Independent toggle command objects.
- Device-specific credential attributes.
- Configuration accessors and canonical serialization.
- Custom Action identity policy.

Preserve existing persistence and recovery safeguards.

Prepare complete replacement configurations.

Test configuration behavior independently where practical.

### Phase 3 — Adapter coordination and consumers

Refactor adapter selection to use declared device types.

Update dispatcher, physical control, startup, diagnostic,
and other configuration consumers.

Preserve existing Roku, Denon, and generic HTTP behavior.

Route Custom Actions through their applicable adapters
while preserving single-command semantics.

Review cache rebuilding, cancellation, and connection cleanup.

Do not enable production LG execution yet.

### Phase 4 — Configuration editor

Implement:

- Compact device table and device-type selectors.
- Dynamic room addition and removal.
- Protocol-aware fundamental and Custom Action editors.
- Independent toggle command editing.
- Automatic Custom Action ID generation.
- Conditional client-key and pairing controls.

Preserve import, save, revision, and Test Remote behavior.

Functional LG pairing remains deferred.

### Phase 5 — Controlled deployment

Deploy a compatible firmware/configuration pair.

Verify startup, configuration loading, room selection,
and basic execution before broader testing.

Retain an external rollback configuration and compatible
firmware.

### Phase 6 — Existing-equipment regression testing

Complete the regression checklist using existing
Roku, Denon, and generic HTTP configurations.

Investigate and correct regressions before introducing
LG runtime execution.

Verify configuration size limits and memory behavior.

### Phase 7 — Documentation and recipe checkpoint

Update authoritative configuration and architecture
documentation to describe the implemented design.

Update recipe files, examples, and development procedures.

Establish a known-good Config v5 baseline recipe.

### Phase 8 — LG integration and experimentation

Prepare a focused LG experimental configuration recipe.

Connect the LG adapter to production device routing.

Implement and test operational pairing.

Test individual SSAP and pointer commands.

Experiment with mixed-protocol Custom Actions.

Resolve asynchronous completion, ordering, timeout,
and failure propagation questions using actual equipment.

Restore the baseline recipe and verify existing operation
and proper LG session retirement.

The detailed implementation sequence may be adjusted
after dependency inspection.

## 20. Regression checklist

### Configuration and persistence

- [ ] Load a valid Config v5 configuration.
- [ ] Reject malformed and unsupported-schema configurations.
- [ ] Validate supported device types and endpoints.
- [ ] Validate HTTP, SSAP, and pointer command structures.
- [ ] Validate independent ON/OFF command objects.
- [ ] Validate applicable device-specific attributes.
- [ ] Preserve intentionally blank destinations and commands.
- [ ] Verify configurations containing one, two, and three rooms.
- [ ] Reject configurations containing no rooms.
- [ ] Verify canonical serialization and revision stability.
- [ ] Verify changed and unchanged save behavior.
- [ ] Reject stale browser revisions.
- [ ] Verify backup rotation and compatible recovery.
- [ ] Verify read-only SERVICE-mode behavior.
- [ ] Verify configuration import and recipe replacement.
- [ ] Verify successful-save OLED feedback.
- [ ] Verify browser watchdog and retry behavior.

### Configuration editor

- [ ] Display and edit configured room names.
- [ ] Add a previously unconfigured room.
- [ ] Remove a configured room with confirmation.
- [ ] Preserve remaining room IDs after removal.
- [ ] Prevent removal of the last configured room.
- [ ] Display and edit device types and endpoints.
- [ ] Display unavailable device types as disabled.
- [ ] Preserve existing fundamental command mappings.
- [ ] Preserve toggle ON/OFF mappings.
- [ ] Display applicable protocol-specific command fields.
- [ ] Validate editable JSON payloads.
- [ ] Identify incompatible commands after device-type changes.
- [ ] Verify conditional credential and pairing controls.
- [ ] Create Custom Actions with automatically generated IDs.
- [ ] Preserve IDs during editing and reordering.
- [ ] Reject duplicate or malformed imported IDs.
- [ ] Preserve Custom Action step ordering and delays.
- [ ] Verify Test Remote room and action selection.

LG-specific editor components may be tested independently
before normal LG device selection is enabled.

### Runtime execution

- [ ] Verify explicit adapter selection.
- [ ] Verify generic HTTP GET and POST commands.
- [ ] Verify Denon persistent TCP volume behavior.
- [ ] Verify Denon HTTP command behavior.
- [ ] Verify Roku ordinary commands.
- [ ] Verify Roku persistent HTTP reuse.
- [ ] Verify Roku tap and sustained-hold behavior.
- [ ] Verify Roku held-volume behavior.
- [ ] Verify physical navigation and playback controls.
- [ ] Verify power and mute toggle histories.
- [ ] Verify physical room selection.
- [ ] Verify Custom Action encoder selection and execution.
- [ ] Verify Custom Action adapter routing.
- [ ] Verify Custom Action single-command semantics.
- [ ] Verify Custom Action delays and queue sequencing.
- [ ] Verify cancellation after execution failure.
- [ ] Verify blank-command and unconfigured-room behavior.
- [ ] Verify configuration changes invalidate stale runtime state.

### Performance and reliability

- [ ] Compare command responsiveness with the existing baseline.
- [ ] Verify rapid navigation and encoder input.
- [ ] Verify OLED responsiveness.
- [ ] Verify adapter diagnostic snapshots.
- [ ] Verify Flight Recorder operation.
- [ ] Measure configuration loading and validation memory usage.
- [ ] Measure configuration save-time memory usage.
- [ ] Verify proposed configuration and HTTP request size limits.
- [ ] Verify memory behavior across repeated saves and actions.
- [ ] Verify CONFIG and RUN operating-mode transitions.
- [ ] Verify connection cleanup during configuration changes.

The previously documented intermittent CONFIG HTTP
socket-send stall remains a separate known investigation.

Do not claim that the configuration redesign resolves
that issue without specific supporting evidence.

### Subsequent LG integration

- [ ] Verify manual client-key entry.
- [ ] Verify pairing initiation, approval, rejection, and cancellation.
- [ ] Verify credential persistence and placeholder handling.
- [ ] Verify SSAP commands without payloads.
- [ ] Verify SSAP commands with structured payloads.
- [ ] Verify pointer commands.
- [ ] Verify mixed-protocol Custom Actions.
- [ ] Investigate asynchronous completion and command ordering.
- [ ] Verify timeout and failure propagation.
- [ ] Verify toggle and Custom Action completion semantics.
- [ ] Verify session retirement after endpoint or credential changes.
- [ ] Restore the baseline recipe and verify normal operation.
- [ ] Verify credentials are excluded from ordinary diagnostics.

## 21. Remaining implementation decisions

The principal configuration architecture decisions
have been established.

Remaining implementation details include:

- Exact registry structure and browser exposure mechanism.
- Configuration module naming and import updates.
- Exact blank-command representation for each command kind.
- Default room and device initialization details.
- Custom Action ID generation mechanism.
- Final configuration and HTTP request size limits.
- Adapter cache invalidation and cleanup implementation.
- Credential presentation and diagnostic sanitization.

These details should be resolved during implementation
without unnecessarily expanding the architecture.

The LG asynchronous execution questions are explicitly
deferred as described in Section 13.

They are not blockers to the configuration refactor.

## 22. Explicitly deferred work

The initial configuration refactor does not include:

- Production LG webOS command routing.
- Functional LG pairing operations and management API.
- Final LG asynchronous execution integration.
- Apple TV protocol implementation.
- Fire TV protocol implementation.
- Arbitrary user-defined device destinations.
- A replacement action queue.
- Automatic legacy schema migration.
- A protocol-aware recipe website.
- A separate configuration profile manager.

Implement foreseeable LG configuration requirements now.

Implement and test LG protocol execution afterward.

Do not implement speculative functionality for future
device types without an established requirement.

## 23. Implementation outcome and sources of truth

**Implementation status: November 24, 2026**

The Chapter 12 configuration redesign has been implemented
and integrated into the operational Clonker firmware.

Config v5 is now the active configuration schema.

This document is retained as the original agreed design
proposal and implementation plan. Its earlier descriptions,
proposed decisions, and verification checklists reflect
the planning stage rather than the current operational state.

### 23.1 Implementation results

| Workstream | Status |
|---|---|
| Config v5 schema and validation | Implemented |
| Central device-type registry | Implemented |
| Typed adapter coordinator | Integrated |
| Protocol-aware command objects | Implemented |
| Configuration activation lifecycle | Verified |
| Physical gesture invalidation | Verified |
| Configuration editor redesign | Verified |
| Stable Custom Action identifiers | Implemented |
| Optional room management | Implemented |
| Config v5 recipe import | Verified |
| Hosted recipe library update | Published and verified end-to-end |
| Test Remote configuration awareness | Implemented and live-tested |
| Configuration persistence optimization | Verified |
| LG SSAP and pointer configuration | Implemented |
| LG client-key editing | Implemented |
| LG pairing control | Present, disabled |
| LG runtime integration | Deferred |
| Apple TV and Fire TV | Reserved future types |

Six focused automated regression suites passed a combined
436 assertions during implementation.

All five existing operational execution paths were exercised
successfully on physical equipment.

Subsequent configuration persistence improvements passed
twenty consecutive changed browser saves, followed by
additional successful post-cleanup regression tests.

The original intermittent management HTTP socket-send
stall remains unresolved.

These results do not imply exhaustive reliability testing
or a complete rerun of every earlier regression suite
against the final optimized persistence implementation.

### 23.2 Current sources of truth

The implemented configuration and operational architecture
are now documented in:

- [Configuration, Persistence & Recovery](CONFIGURATION.md)
- [Architecture](ARCHITECTURE.md)
- [Firmware Network](FIRMWARE_NETWORK.md)
- [Development History](DEVELOPMENT_HISTORY.md)

These documents supersede the planning-stage descriptions
in this proposal wherever implementation details differ.

The active firmware remains the authoritative source
for exact behavior and implementation constants.

### 23.3 Future LG integration

Experimental LG protocol knowledge resides primarily in:

- [LG webOS draft adapter](../firmware/clonker/devices/lg_webos.py)
- [Firmware laboratory tests](../firmware/tests/)

The draft adapter remains intentionally disconnected
from operational dispatch.

The configuration redesign establishes its integration
foundation without prematurely committing to asynchronous
completion, authenticated session, or pairing behavior.

The LG-specific implementation and verification checklists
remain useful starting points for the next integration phase.

Preserve the existing Dumb Queue™, operational adapter
behavior, and validation boundaries.

**The configuration foundation is ready.
The Monster's next language awaits.**

---

**THE CLONKER 10000**

*The Monster Gets Organized.*

**Less sleek. More CLONK.**
