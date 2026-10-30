# Documentation for Humans, AI, and the Occasional Mad Scientist

*A documentation philosophy born from THE CLONKER 10000.*

## Why This Document Exists

THE CLONKER 10000 started as a silly little DIY remote control project. Somewhere along the way, it became an experiment in long-term human–AI collaboration.

One unexpected result: we've produced more documentation for this little monster than many substantially larger traditional software projects.

Some of that is genuinely valuable. Some of it may be excessive.

The challenge is to preserve the benefits without allowing documentation to become a second project whose sole purpose is maintaining the documentation.

Our goal is simple:

> Document enough that a new human or AI collaborator can become productive quickly, but not so much that maintaining the documentation competes with building the product.

## Four Guiding Principles

### 1. Human-First Readability

Someone visiting the GitHub repository should be able to understand the project, enjoy its personality, and find what interests them without navigating an encyclopedia.

- Keep the README approachable and engaging.
- Introduce concepts before diving into implementation details.
- Use clear headings, meaningful filenames, and useful links.
- Preserve the project's humor and personality.
- Make detailed technical information available without forcing everyone to read it.

Documentation should invite exploration, not demand endurance.

### 2. AI-Friendly Structure

A new AI development session should be able to locate authoritative information and resume productive work without rereading the entire repository.

- Maintain clear entry points into the documentation.
- Organize reference material around specific responsibilities.
- Distinguish current implementation from historical discussion.
- Record important design decisions and their rationale.
- Make relationships between components discoverable.
- Favor selective retrieval over loading everything.

AI-friendly documentation doesn't require complicated AI-specific formats. Well-organized Markdown is an excellent starting point.

### 3. Minimal Duplication

Each important technical fact should have one authoritative home.

Other documents should link to that source rather than maintain competing copies.

This reduces:

- Contradictory information.
- Outdated implementation descriptions.
- Unnecessary maintenance.
- Confusion about which document represents the current design.

Some repetition is useful for orientation, but detailed specifications should not be independently maintained in multiple places.

### 4. Proportional Maintenance

Documentation should support development, not become a tax on experimentation.

A five-line firmware change shouldn't require updating four Markdown documents unless the change genuinely affects four different aspects of the design.

Document significant decisions, interfaces, behavior changes, and verified results.

Avoid documenting every trivial implementation detail or temporary experiment.

The amount of documentation should be proportional to its long-term value.

## A New Audience: The Next AI Session

Traditional software documentation primarily serves people who need to understand, operate, or maintain a system.

AI-assisted development introduces another audience: the next AI session that needs to work on the project.

That collaborator benefits from knowing:

- Which decisions are final and which remain experimental.
- Which source files implement particular behaviors.
- Which assumptions should not be changed accidentally.
- Which tests have actually been performed on hardware.
- Which features remain incomplete.
- Where development should resume.

These details also improve traditional engineering practices.

The objective isn't to document everything. It's to preserve the information necessary for continuity.

## Organize for Selective Retrieval

As documentation grows, the most frequently consulted references should remain relatively small and focused.

A useful hierarchy is:

1. **Orientation:** What the project is, how it works, and where to look next.
2. **Working references:** Current specifications, interfaces, procedures, and implementation details.
3. **Deep references and history:** Extended explanations, experiments, superseded decisions, and development records.

Large historical archives aren't inherently a problem if they're rarely needed in full.

Frequently consulted documents deserve more attention to size and focus.

However, splitting documents merely to make them smaller can be counterproductive. Excessive fragmentation makes information harder to discover and maintain.

The objective is to minimize the amount of material needed for a particular task while preserving the relationships between components.

## Current Truth Versus Historical Record

Documentation should make it easy to distinguish what the system **does today** from what we previously considered, attempted, or abandoned.

Current technical references should describe the implemented design.

Development history should preserve the experiments, alternatives, failures, and reasoning that led us there.

Both are valuable. They simply serve different purposes.

## A Practical Test for Every Document

When reviewing the documentation structure, ask:

> What job does this document perform, and who needs to read it?

If the answer isn't clear, consider whether the document should be shortened, split, consolidated, or repositioned.

Before introducing new documentation infrastructure, ask whether ordinary Markdown, meaningful filenames, cross-references, and disciplined organization would accomplish the same thing.

Prefer the simplest system that works.

## Lessons for Future Projects

Not every project needs thousands of lines of documentation.

A sensible starting point might include:

- A concise README.
- An architecture overview when warranted.
- A short record of important design decisions.
- Focused references added as real development needs emerge.

Let documentation grow in response to the project's complexity and collaboration requirements.

THE CLONKER 10000 has accumulated unusually extensive documentation partly because it must preserve continuity across many AI-assisted development sessions.

That is a legitimate requirement, but also an opportunity to learn where documentation provides value and where it becomes excessive.

## The Clonker Standard

We want documentation that is:

- **Readable** enough for curious humans.
- **Structured** enough for productive AI collaboration.
- **Accurate** enough to trust.
- **Concise** enough to maintain.
- **Entertaining** enough to reflect the project that inspired it.

And above all:

**We should spend more time building the Monster than documenting the philosophical significance of a button going CLONK.**

---

*THE CLONKER 10000*

*Less sleek. More CLONK.*
