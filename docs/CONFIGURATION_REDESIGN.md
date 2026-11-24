# The Clonker 10000 — Configuration Redesign

**Proposed:** November 24, 2026  
**Origin:** Chapter 11  
**Target:** Chapter 12  
**Status:** Design proposal — not implemented  
**Current schema:** Config v4  
**Proposed schema:** Config v5  

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

Rather than incrementally extending the existing HTTP-oriented
configuration model, Chapter 12 will establish a more
explicit and extensible device configuration architecture.

The redesign should preserve the flexibility and simplicity
of the existing Clonker while removing assumptions that
all devices communicate through ordinary HTTP requests.

## 2. Relationship to the LG webOS adapter

The standalone experimental adapter:

`firmware/clonker/devices/lg_webos.py`

is an intentional architectural reference for this redesign,
not abandoned experimental code.

It consolidates the successful Chapter 11 laboratory
experiments, including:

- WebSocket transport and connection lifecycle.
- SSAP registration and request/response correlation.
- Separate pointer input connections.
- Cooperative receive processing.
- Pairing and client-key verification.
- Temporary development credentials.
- Transport and pairing diagnostics.

The adapter remains intentionally disconnected from
production device routing.

Review this adapter and the associated laboratory scripts
before finalizing the new configuration schema, device
registry, command representation, and adapter interfaces.

The laboratory scripts are located in
`firmware/tests/test_lg_webos_*.py`.

The configuration redesign is undertaken in direct support
of future LG webOS integration.

**LG integration is deferred, but its requirements are not.**

The immediate objective is to establish and regression-test
the redesigned configuration using existing supported devices
before connecting the LG adapter to the running application.

Future Apple TV support may benefit from the same
architectural foundation, but its specific protocol
requirements remain to be investigated.

## 3. Design objectives

- Explicitly identify the type of each configured device.
- Separate device identity, role, type, endpoint, and commands.
- Select adapters by configured device type.
- Preserve editable fundamental and custom action commands.
- Accommodate device-specific configuration attributes.
- Provide a compact, extensible configuration editor.
- Automatically generate stable Custom Action IDs.
- Preserve existing configuration persistence safeguards.
- Avoid unnecessary legacy schema compatibility.
- Preserve existing operational behavior through regression testing.
- Prepare for pairing without implementing its UI prematurely.

## 4. Architectural invariants

The redesign must preserve the following principles:

- There remains one shared Dumb Queue™.
- Browser and physical controls use the same execution path.
- Fundamental actions retain their established identities.
- Custom actions retain their ordered step semantics.
- Device adapters own protocol-specific behavior.
- The configuration layer owns configuration data and persistence.
- Display names are not internal identifiers.
- Blank destinations and fundamental commands remain valid
  intentional no-ops.
- No implicit fallback to another room or destination.
- No automatic command replay after transport failure.
- Configuration validity does not imply equipment reachability
  or successful command execution.

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

Do not infer the device type from its role, endpoint port,
command syntax, or display label.

Retain the existing stable room identifiers and support for
one to three configured rooms.

Future custom destinations remain outside the immediate
redesign scope.

### 5.2 Typed device records

Replace the existing endpoint-string representation with
structured device records.

Conceptual Config v5 device fragment:

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

This is an illustrative fragment, not a complete deployable
configuration.

The final field names and exact validation rules should
be established after inspecting the current implementation.

Existing IPv4 and optional port syntax should remain
supported unless a specific protocol requires an extension.

### 5.3 Device-specific attributes

Device types may require additional configuration attributes.

A future LG webOS device could resemble:

```json
{
  "type": "lg-webos",
  "endpoint": "192.168.50.47:3000",
  "client_key": "PASTE_OR_PAIR_CLIENT_KEY_HERE"
}
```

The client key belongs to the configured device, not to
individual fundamental commands or custom action steps.

Avoid adding unrelated authentication fields to every device.

Device-specific attributes should be validated according
to the declared device type.

Whether these attributes reside directly in the device
record or in a nested settings object remains an open
schema design decision.

## 6. Device-type registry

Consider a small centralized registry of supported device types.

Proposed internal identifiers:

| Type ID | Display label | Status |
|---|---|---|
| `generic-http` | Generic HTTP | Operational |
| `denon` | Denon AVR | Operational |
| `roku` | Roku ECP | Operational |
| `lg-webos` | LG webOS | Experimental |
| `apple-tv` | Apple TV | Planned |
| `fire-tv` | Amazon Fire TV | Planned |

Internal identifiers must remain independent of user-facing
labels.

The registry may describe:

- Device type identifier.
- User-facing display label.
- Associated adapter.
- Default endpoint port, where appropriate.
- Supported command representation.
- Additional configuration attributes.
- Pairing capability.
- Implementation availability.

Avoid duplicating device-type knowledge independently
throughout the firmware and browser editor.

The exact registry implementation and browser exposure
mechanism require further design.

Experimental and planned device types may appear in
the configuration editor's device-type selector.

Types that are not yet operational must be displayed
as disabled (greyed-out), non-selectable options.

Their presence communicates intended future support
without implying that their adapters are operational.

Device-type availability should be driven by the
central registry rather than independently hard-coded
into the browser editor.

Device-type validation should reuse the central registry
and remain deliberately simple. Avoid introducing additional
validation machinery solely to defend against manually
modified configuration files containing unavailable device
types.

## 7. Configuration editor redesign

### 7.1 Compact device table

Replace the existing device address fields with a compact,
vertically organized table within each room configuration.

Conceptual layout:

| Role | Device type | IP address : port |
|---|---|---|
| TV | Type selector | Editable endpoint |
| AVR | Type selector | Editable endpoint |
| Streaming | Type selector | Editable endpoint |

The room name remains independently editable.

Each row contains:

- A recognizable device role label.
- A supported device-type selector.
- An editable endpoint.

Device type selection may eventually provide sensible
default ports, but must not silently overwrite existing
user-entered endpoints or commands.

### 7.2 Conditional device-specific controls

When a selected device type requires pairing, display
a pairing button alongside an editable client-key field
associated with that device row.

Both controls should be available together, allowing
the user to either initiate pairing or manually enter
an existing client key.

Pairing-capable device rows should provide:

- An editable client-key field.
- A pairing button.
- Pairing progress and result indication.
- An indication of credential availability.

These controls should appear conditionally according
to the selected device type's declared capabilities.

Other device-specific configuration attributes may
be accommodated using the same approach.

The layout should remain compact for ordinary Roku,
Denon, and generic HTTP configurations.

Actual pairing functionality remains deferred until
the redesigned configuration architecture is operational
and regression-tested.

### 7.3 Preserve existing editor capabilities

Retain:

- Room configuration.
- Fundamental action editing.
- Toggle ON/OFF command editing.
- Custom action creation and editing.
- Ordered custom action steps and delays.
- Revision-aware saves.
- Configuration import and recipe browsing.
- Test Remote functionality.
- Existing save confirmation and error handling.

Changing a device type must not silently discard or rewrite
the user's existing commands.

Incompatible commands should be identified clearly.

## 8. Explicit adapter selection

### 8.1 Current approach

The current application uses configured endpoints,
HTTP methods, and command paths.

Specialized adapter selection relies partly on recognizing
Roku and Denon command signatures.

This was practical for the original HTTP-oriented design.

### 8.2 Proposed approach

The configured target identifies a device record.

The device record explicitly identifies the device type.

The device type determines the adapter.

Conceptual execution flow:

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
need to infer a device's identity from its command syntax.

### 8.3 Protocol-specific transport decisions

Explicit adapter selection does not eliminate all
command-specific recognition.

It changes where that recognition belongs.

The Denon adapter may still recognize volume commands
that use its specialized persistent TCP connection.

The Roku adapter may still recognize commands eligible
for persistent HTTP, native held-button behavior, or
other specialized execution policies.

LG webOS may distinguish SSAP requests from pointer
input commands.

These are internal adapter decisions, not device-type
discovery mechanisms.

Preserve the useful protocol-specific diagnostics and
transport behavior established in earlier chapters.

### 8.4 Adapter cache and lifecycle

Review the existing adapter cache, configuration accessors,
readiness checks, execution delegation, cancellation,
polling, and connection cleanup.

Changed configurations must not leave stale device-type
associations, endpoint associations, or authenticated
sessions active.

Preserve the existing changed-save and unchanged-save
semantics.

Do not reintroduce repeated full configuration validation
into latency-sensitive execution paths.

## 9. Command configuration

### 9.1 Preserve user-editable commands

Editable commands are a deliberate Clonker capability.

Users should remain able to configure the commands associated
with fundamental actions and custom action steps.

Explicit device typing must not turn the Clonker into a
fixed, hard-coded command library.

The first implementation phase should preserve the existing
HTTP method/path representation and behavior where practical.

However, the new schema must be reviewed against the
requirements of the draft LG webOS adapter before it
is finalized.

### 9.2 Future command representations

Different protocols may require different command data.

Examples:

| Protocol | Command | Additional data |
|---|---|---|
| Roku ECP | `/keypress/Home` | POST |
| Denon HTTP | `/goform/formiPhoneAppDirect.xml?MVUP` | GET |
| LG SSAP | `ssap://audio/volumeUp` | None |
| LG SSAP | `ssap://audio/setMute` | JSON payload |
| LG Pointer | `HOME` | None |

These examples illustrate protocol requirements, not
a finalized Config v5 command schema.

A future LG SSAP command may contain a configurable URI
and optional structured payload.

Pointer input commands may require a distinct command
kind or another unambiguous representation.

Do not assume every future command can be expressed as
an HTTP method and slash-prefixed path.

Review both fundamental actions and custom action steps
when establishing the command model.

Toggle actions must also accommodate distinct ON and OFF
command arguments where required.

### 9.3 Protocol request identifiers

An LG SSAP request can resemble:

```json
{
  "id": "clonker-42",
  "type": "request",
  "uri": "ssap://audio/volumeUp"
}
```

The request ID is generated by the adapter for response
correlation.

It is not a user-editable configuration attribute.

Some commands contain an additional identifier within
their payload:

```json
{
  "id": "clonker-43",
  "type": "request",
  "uri": "ssap://system.launcher/launch",
  "payload": {
    "id": "com.webos.app.home"
  }
}
```

The payload ID identifies the application to launch.

Unlike the outer request ID, it is command-specific data
and may legitimately be configurable.

Keep these meanings separate.

### 9.4 Asynchronous completion

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

Review asynchronous failure propagation, response deadlines,
toggle advancement, custom action step completion, and
queue cancellation before enabling LG execution.

Do not change existing completion semantics speculatively.

## 10. Custom Action IDs

### 10.1 Remove user editing

Custom Action IDs were originally exposed as editable
configuration fields.

This flexibility is unnecessary for ordinary users and
creates avoidable opportunities for duplicate or unstable
identifiers.

The redesigned editor should generate these IDs automatically.

Display the ID in smaller, read-only text for diagnostic
and development purposes.

### 10.2 Identity rules

- Generate an ID when creating a custom action.
- Preserve the ID when renaming or editing an action.
- Preserve the ID when reordering actions.
- Generate a new ID when duplicating an action, if supported.
- Never derive identity solely from the display name.
- Never renumber existing actions merely because one is deleted.
- Validate imported IDs and reject invalid duplicates.
- Do not silently rewrite existing valid IDs.

Config v4 currently requires uniqueness within each room.

The proposed redesign should consider configuration-wide
uniqueness for newly generated IDs.

Whether to enforce configuration-wide uniqueness for all
imported actions should be decided after reviewing current
consumers and existing configuration data.

The generation mechanism must work within CircuitPython
and browser resource constraints.

Avoid unnecessary complexity or external dependencies.

### 10.3 Distinct identifier classes

Keep the following concepts separate:

| Identifier | Purpose |
|---|---|
| Room ID | Stable configured room |
| Device ID | Stable configured destination |
| Device type ID | Adapter and capability selection |
| Fundamental Action ID | Application-defined action |
| Custom Action ID | Stable user-defined action |
| Protocol request ID | Transient network correlation |

These identifiers have different scopes and lifetimes.

## 11. Future pairing architecture

Pairing is a device protocol operation.

The configuration interface orchestrates the user interaction
and persists the resulting credentials.

The draft LG adapter already contains experimental pairing
helpers and client-key verification functionality.

Review and reuse those helpers rather than implementing
LG-specific WebSocket registration inside the browser
management or configuration modules.

Conceptual pairing flow:

1. User selects a configured device requiring pairing.
2. Configuration UI requests a pairing operation.
3. The appropriate adapter initiates pairing.
4. The user approves the request on the equipment.
5. The adapter cooperatively processes the result.
6. The resulting credential is returned to the configuration layer.
7. The user reviews and saves the updated configuration.

The approval wait must not block the main cooperative
scheduler for the entire human-interaction timeout.

Cancellation, rejection, timeout, and resource cleanup
must be handled explicitly.

Pairing success and configuration persistence are separate
operations.

Do not assume successful pairing means that the resulting
credential has already been saved.

The exact management API and pairing state model remain
future design work.

### 11.1 Configuration validity versus device readiness

A valid configuration may contain:

- A blank endpoint.
- An intentionally blank fundamental command.
- A device awaiting pairing.
- A missing or placeholder credential.

Such a configuration should remain importable and savable.

A device requiring authentication should not be considered
ready for execution until the necessary credential is
available.

An unready device must not prevent unrelated configured
devices from operating normally.

Define the exact unavailable-device and custom-action
failure semantics before enabling authenticated adapters.

### 11.2 Credential handling

Actual client keys and authentication tokens must not be
committed to the public repository or published in recipes.

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

## 12. Schema versioning and replacement

The current active schema is Config v4.

The proposed redesign should increment the schema version
to Config v5 when the incompatible changes are implemented.

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

Review storage and HTTP request limits against the new
configuration size.

Current documented limits include:

- 8192 bytes for stored configuration.
- 10240 bytes for incoming management HTTP requests.

Measure representative configurations before changing
these limits.

Avoid arbitrary increases that could create unnecessary
memory pressure on the Pico.

## 13. Recipe Configuration and Credential Sanitization

The Configuration Recipe Library distributes complete
replacement configuration JSON files.

It should remain a simple publication and download
mechanism rather than becoming a protocol-aware
configuration service.

Verify that the existing recipe website does not depend
on the old schema before assuming that replacing the
downloadable JSON is sufficient.

Update the downloadable recipe and any associated schema
version descriptions when Config v5 is introduced.

### 13.1 Publication workflow

The maintainer may provide an exported, working,
minified configuration JSON for recipe preparation.

The publication preparation process should:

1. Parse the working JSON.
2. Produce a readable, indented representation.
3. Preserve device types, commands, action IDs, custom
   action ordering, and step delays.
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

### 13.2 Recipe import

The user should be able to import a recipe, review it,
edit device addresses and credentials, and explicitly save.

Placeholder credentials must be recognized as unavailable
credentials rather than transmitted to equipment as if
they were real authentication keys.

Pretty-printed recipe files may be larger than their
compact stored representation.

Review import size limits and canonicalization behavior
as part of the redesign.

## 14. Application impact inventory

Before implementation, inspect the current repository and
identify every consumer of the configuration schema.

Areas requiring review include:

- Configuration validation and normalization.
- Configuration accessors and active RAM state.
- Revision calculation and persistence.
- Startup loading and recovery.
- Adapter cache construction.
- Device adapter selection and execution.
- Action dispatcher and Dumb Queue integration.
- Fundamental action and toggle handling.
- Custom action admission and sequencing.
- Physical control coordination.
- OLED feedback and custom action selection.
- Configuration editor HTML and JavaScript.
- Management HTTP API.
- Test Remote page.
- Recipe browsing and JSON import.
- Repository examples and sample configurations.
- Diagnostic and Flight Recorder behavior.
- Existing standalone tests and regression procedures.

Start with the authoritative configuration implementation:

`firmware/clonker/device_config_v2.py`

Its historical filename does not indicate the current
schema version.

Inspect the current code rather than relying solely
on historical documentation or conversation summaries.

The standalone LG draft must be included in this review
even though it is not yet a production configuration consumer.

## 15. Proposed implementation sequence

### Phase 1 — Inventory and design

Inspect the current repository and working configuration.

Identify configuration consumers, adapter boundaries,
validation rules, UI dependencies, and test coverage.

Review the LG draft and laboratory findings.

Finalize the Config v5 device and command representations
before undertaking cascading changes.

### Phase 2 — Configuration engine

Implement typed device records, validation, accessors,
and canonical serialization.

Establish the device-type registry and Custom Action
ID policy.

Prepare complete replacement configurations.

### Phase 3 — Adapter coordination

Refactor adapter selection to use declared device types.

Preserve existing Roku, Denon, and generic HTTP
transport behavior.

Review cache rebuilding and connection cleanup.

### Phase 4 — Configuration editor

Implement the compact device table and type selectors.

Remove Custom Action ID editing and implement automatic
ID generation.

Preserve existing command editing, import, save, and
Test Remote functionality.

Pairing controls remain deferred.

### Phase 5 — Controlled deployment

Deploy a compatible firmware/configuration pair.

Verify startup, configuration loading, room selection,
and basic execution before broader testing.

### Phase 6 — Regression testing

Complete the regression checklist below using the
existing supported devices.

Investigate and correct regressions before introducing
LG runtime execution.

### Phase 7 — Documentation checkpoint

Update the authoritative configuration and architecture
documentation to describe the implemented design.

Update recipe files, examples, and development procedures.

Consolidate this proposal into the permanent documentation
or retain it clearly as historical design material.

The implementation sequence may be adjusted after
dependency inspection.

## 16. Regression checklist

### Configuration and persistence

- [ ] Load a valid Config v5 configuration.
- [ ] Reject malformed and unsupported-schema configurations.
- [ ] Validate all supported device types and endpoints.
- [ ] Preserve intentionally blank destinations and commands.
- [ ] Verify canonical serialization and revision stability.
- [ ] Verify changed and unchanged save behavior.
- [ ] Reject stale browser revisions.
- [ ] Verify backup rotation and compatible recovery.
- [ ] Verify read-only SERVICE-mode behavior.
- [ ] Verify configuration import and recipe replacement.
- [ ] Verify successful-save OLED feedback.
- [ ] Verify browser watchdog and retry behavior.

### Configuration editor

- [ ] Display and edit all configured room names.
- [ ] Display and edit device types and endpoints.
- [ ] Preserve existing fundamental command mappings.
- [ ] Preserve toggle ON/OFF mappings.
- [ ] Create custom actions with automatically generated IDs.
- [ ] Preserve IDs during editing and reordering.
- [ ] Reject duplicate or malformed imported IDs.
- [ ] Preserve custom action step ordering and delays.
- [ ] Verify Test Remote room and action selection.

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
- [ ] Verify custom action encoder selection and execution.
- [ ] Verify custom action delays and queue sequencing.
- [ ] Verify cancellation after execution failure.
- [ ] Verify blank-command and unconfigured-room behavior.
- [ ] Verify configuration changes invalidate stale runtime state.

### Performance and reliability

- [ ] Compare command responsiveness with the existing baseline.
- [ ] Verify rapid navigation and encoder input.
- [ ] Verify OLED responsiveness.
- [ ] Verify adapter diagnostic snapshots.
- [ ] Verify Flight Recorder operation.
- [ ] Verify memory behavior across repeated saves and actions.
- [ ] Verify CONFIG and RUN operating-mode transitions.
- [ ] Verify connection cleanup during configuration changes.

The previously documented intermittent CONFIG HTTP
socket-send stall remains a separate known investigation.

Do not claim that the configuration redesign resolves
that issue without specific supporting evidence.

## 17. Explicitly deferred work

The initial configuration redesign does not include:

- Production LG webOS command routing.
- Production LG pairing UI or management API.
- Final LG asynchronous execution integration.
- Apple TV protocol implementation.
- Arbitrary user-defined device destinations.
- A replacement action queue.
- Automatic legacy schema migration.
- A protocol-aware recipe website.

The architecture must accommodate foreseeable LG
requirements without implementing speculative functionality.

## 18. Open design questions

Resolve these during the Chapter 12 source inventory:

- Exact Config v5 device record structure.
- Location and representation of device-specific attributes.
- Registry ownership and browser exposure.
- Device-type availability and blank-device representation.
- Default port behavior.
- Command representation for non-HTTP protocols.
- Toggle command argument representation.
- Custom Action ID generation and uniqueness scope.
- Configuration and HTTP request size limits.
- Adapter cache invalidation and session cleanup.
- Device readiness and unavailable-command semantics.
- Future credential persistence and management security.
- Asynchronous response and custom action completion semantics.

These are design questions, not authorization to expand
the immediate implementation scope.

## 19. Sources of truth

Until the redesign is implemented, the current working
configuration architecture remains documented in:

- [Configuration, Persistence & Recovery](CONFIGURATION.md)
- [Architecture](ARCHITECTURE.md)
- [Firmware Network](FIRMWARE_NETWORK.md)
- [Development History](DEVELOPMENT_HISTORY.md)

Experimental LG protocol knowledge resides primarily in:

- [LG webOS draft adapter](../firmware/clonker/devices/lg_webos.py)
- [Firmware laboratory tests](../firmware/tests/)

This proposal records the intended direction and agreed
design objectives for Chapter 12.

It does not supersede the existing implemented schema.

---

**THE CLONKER 10000**

*The Monster Gets Organized.*

**Less sleek. More CLONK.**
