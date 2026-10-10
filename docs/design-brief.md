# Design brief and acceptance checklist

For new designs, use the [validated project format](projects.md): `init` creates
brief.json, and `doctor` derives acceptance entries from its requirements. This
guide explains how to fill those records. For an existing project, map its records
to the same concepts without duplicating requirements; the manual table below is
also useful for reviewing historical records.
The vehicle and building entries below are documentation examples, not shipped
models or evidence of completed checks.

## Record the brief once

| Field | What to record |
|---|---|
| Subject and use | What to represent; display, handling or play expectations |
| Size and scale | Target dimensions or scale, units and acceptable compromises |
| Construction | Required part families/build style; real-part-only constraints |
| Appearance | Recognizable features, colours, detail priorities and reference IDs |
| Functions | Requested movement, removable sections or alternate configurations |
| Sourcing | Region, budget/currency, owned parts, condition preferences, evidence dates; unknown if unspecified |
| Decoration | Whether stickers are allowed and which features may use them |
| Deliverables | CAD, views, BOM/order format, instructions and trial modules requested |
| Coordinates | Model front/up axes and mappings to reference views |

Classify each requirement as a hard constraint or preference. Record assumptions
explicitly; do not turn a convenient implementation choice into a user requirement.
A source may be a user message, photograph, dimensioned drawing or construction
manual. Record URL/file identity, edition, retrieval status, checksum where
available, figure/PDF page and what it actually supports. Mark inaccessible
sources and uncertain interpretations.

Keep decisions beside the requirements: decision ID, affected requirement IDs,
date, choice, reason, evidence, and whether it is an agent assumption or a
user-accepted compromise. Do not claim approval that was never given.

Normal releases reconcile requested deliverables, named requirement views and
sticker permission with the captured brief. Use a labelled draft for a partial
delivery. Accepted changes need an explicit brief revision and decision record;
neither a stage override nor free-text decision silently waives a hard constraint.
See [release policy](releases.md) for the automated checks and remaining limits.

## Trace each requirement to a check

Keep one row per independently reviewable requirement. For new projects,
brief.json.requirements is the single requirement record; reference its IDs from
decisions, views and reports rather than maintaining a second copy of the text. Split a feature into
multiple rows when its appearance, nominal connection and physical behaviour
need different validation methods.

| ID | Requirement and priority | Evidence | Assembly/instances | Required view | Method and acceptance criterion | Result and revision |
|---|---|---|---|---|---|---|
| REQ-001 | Describe one feature; hard/preference | Source IDs or user request | Planned group; actual IDs when authored | Named view/detail | Measurable check or explicit visual judgment | not-tested; pending CAD |

Replace planned groups with actual instance/group IDs during authoring. A missing
assembly, evidence source or view stays visibly unresolved. Never invent a report
hash before generating the model. For visual judgments, record reviewer, date,
view and rationale; for automated results, reference the actual report and hash.

Use pass, fail, unknown and not-tested according to [validation levels](validation-levels.md).
“Not applicable” needs a reason and must not be counted as pass. Changing a model
invalidates affected findings; a sourcing compromise must not erase an unmet
appearance requirement. Keep any accepted deviation in the decision record.

## Worked planning examples

These fictional briefs exercise the workflow without prescribing dimensions,
colours or construction style for every model.

**Small wheeled vehicle:** A display model with four rolling wheels and a
recognizable cab; stickers optional. Size and purchasing region are unspecified.
Record size as a design assumption before laying out the chassis; leave region
unknown until sourcing matters. Plan `chassis`, `front_axle`, `rear_axle` and
`cab` assemblies. First investigate axle support and wheel retention.

| ID | Requirement | Evidence | Assembly | View | Check | Initial result |
|---|---|---|---|---|---|---|
| V-01 | All four wheels have nominal attachment paths | Example brief; reviewed connector declarations needed | Axles and chassis | Underside and axle detail | Declared wheel/axle/mount interfaces reach chassis root with complete coverage | not-tested |
| V-02 | Wheels roll without rubbing | Example brief | Wheels and body | Side and underside | Manual clearance review, then physical rolling trial; record tested configuration | not-tested |
| V-03 | Cab remains recognizable | Example brief; subject reference to be selected | Cab | Front and opposite-side overview | Compare silhouette/proportions to recorded reference and explain judgment | not-tested |

**Small building:** A display building with a doorway and supported roof;
stickers unnecessary. Record a provisional footprint as an assumption. Plan
`base`, `walls`, `opening` and `roof` assemblies. First investigate wall overlap
and support over the opening. Do not copy the vehicle's axle workflow.

| ID | Requirement | Evidence | Assembly | View | Check | Initial result |
|---|---|---|---|---|---|---|
| B-01 | Walls connect to the base | Example brief; reviewed stud/socket declarations needed | Base and walls | Rear and wall/base detail | Declared interfaces reach base root with complete coverage | not-tested |
| B-02 | Roof has nominally connected supports | Example brief | Roof and walls | Cutaway plus full rear view | Check support paths and seating; strength remains a separate physical test | not-tested |
| B-03 | Doorway is visible and unobstructed | Example brief | Opening | Front and opening detail | Visual inspection against intended opening; record dimensions from CAD | not-tested |

Both briefs can proceed through evidence gathering, structure, details, checks,
visual review, sourcing and delivery without a prior release or spacecraft data.
Both still need part selection and project-local authoring until P2 ships. These
are planning walkthroughs, not substitutes for the executable examples in P2.
