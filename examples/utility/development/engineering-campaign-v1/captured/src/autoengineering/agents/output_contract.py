"""Model-visible handoff structure, derived from the authoritative record fields.

This is instructional JSON Schema, not a second acceptance engine. Record parsing,
exact grants, phase checks and the scientific controller remain authoritative.
No host SDK, credentials or scientific execution is imported here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import MISSING, fields, is_dataclass
from types import UnionType
from typing import Literal, Union, get_args, get_origin, get_type_hints

from autoengineering.campaign.serialization import Record, canonical_json
from autoengineering.campaign.records import identifier

from .permissions import validate_assignment
from .records import (
    CandidateBrief,
    ImplementationBundle,
    NextStep,
    ReviewFindings,
    RoleHandoff,
    SINGLE_ROLE,
    SourceDraft,
    SuppliedConfiguration,
)

VERSION = "role-output-contract-1.3"
MAX_BYTES = 32768
IDENTIFIER = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$"
SHA256 = r"^[0-9a-f]{64}$"


class _Schema:
    def __init__(self):
        self.definitions = {}
        self.types = {}

    def annotation(self, annotation):
        origin, args = get_origin(annotation), get_args(annotation)
        if origin in (Union, UnionType):
            return {"anyOf": [self.annotation(value) for value in args]}
        if origin is Literal:
            return {"enum": list(args)}
        if origin is tuple:
            if len(args) == 2 and args[1] is Ellipsis:
                return {"type": "array", "items": self.annotation(args[0])}
            return {
                "type": "array",
                "prefixItems": [self.annotation(v) for v in args],
                "items": False,
                "minItems": len(args),
                "maxItems": len(args),
            }
        if origin in (dict, Mapping):
            if args[0] is not str:
                raise TypeError("output contract requires string mapping keys")
            return {"type": "object", "additionalProperties": self.annotation(args[1])}
        if annotation is type(None):
            return {"type": "null"}
        if annotation in (str, int, float, bool):
            return {
                "type": {str: "string", int: "integer", float: "number", bool: "boolean"}[
                    annotation
                ],
                **({"pattern": r"\S"} if annotation is str else {}),
            }
        if (
            isinstance(annotation, type)
            and issubclass(annotation, Record)
            and is_dataclass(annotation)
        ):
            name = annotation.__name__
            if name in self.types and self.types[name] is not annotation:
                raise TypeError("output contract record names collide")
            if name not in self.definitions:
                self.types[name] = annotation
                self.definitions[name] = {}
                self.definitions[name] = self.record(annotation)
            return {"$ref": f"#/$defs/{name}"}
        raise TypeError(f"unsupported output field annotation: {annotation}")

    def record(self, kind, *, overrides=None):
        annotations = get_type_hints(kind)
        overrides = overrides or {}
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                f.name: overrides[f.name]
                if f.name in overrides
                else self.annotation(annotations[f.name])
                for f in fields(kind)
            },
            "required": [
                f.name
                for f in fields(kind)
                if f.default is MISSING and f.default_factory is MISSING
            ],
        }


def _enum(schema, values):
    values = list(values)
    return {**schema, **({"enum": values} if values else {"not": {}})}


def _outputs(task, generated):
    if task.role == SINGLE_ROLE:
        return (NextStep, CandidateBrief, SuppliedConfiguration, ReviewFindings)
    if task.role == "implementer":
        if task.expected_schema == "role-handoff-1.1":
            if not generated:
                raise ValueError("source-draft output requires generated mode")
            return (SourceDraft,)
        return (
            (SuppliedConfiguration, ImplementationBundle) if generated else (SuppliedConfiguration,)
        )
    return {
        "orchestrator": (NextStep,),
        "investigator": (CandidateBrief,),
        "reviewer": (ReviewFindings,),
    }[task.role]


def output_contract(
    task,
    invocation_id,
    *,
    permitted_implementations,
    generated=False,
    candidate_id=None,
    evaluation_id=None,
):
    """Bind every field/type plus current context into a bounded instruction document.

    Constraints involving other artifacts, physical work, identities or scientific
    state still need their existing validators. This document creates no grant.
    """
    validate_assignment(task)
    identifier(invocation_id)
    for value in (candidate_id, evaluation_id):
        if value is not None:
            identifier(value)
    schema = _Schema()
    outputs = _outputs(task, generated)
    root = schema.record(
        RoleHandoff, overrides={"output": {"oneOf": [schema.annotation(k) for k in outputs]}}
    )
    props = root["properties"]
    for name, value in {
        "schema_version": task.expected_schema.removeprefix("role-handoff-"),
        "task_id": task.id,
        "invocation_id": invocation_id,
        "role": task.role,
        "campaign_revision": task.campaign_revision,
    }.items():
        props[name] = {**props[name], "const": value}
    props["id"] = {
        "type": "string",
        "pattern": IDENTIFIER,
        "description": "A new unique handoff identifier, not the task or invocation ID.",
    }
    props["supersedes"] = {"anyOf": [{"type": "string", "pattern": IDENTIFIER}, {"type": "null"}]}
    props["proposed_next_action"] = _enum(props["proposed_next_action"], task.allowed_operations)
    granted = [g.artifact.sha256 for g in task.grants]

    def evidence_items():
        item = _enum({"type": "string", "pattern": SHA256}, granted)
        return {"type": "array", "items": item, "maxItems": len(granted), "uniqueItems": True}

    props["supporting_artifact_ids"] = evidence_items()
    for name, definition in schema.definitions.items():
        properties = definition["properties"]
        for key in properties:
            if key in ("id", "candidate_id", "target", "implementation_id", "evaluation_id"):
                properties[key] = {"type": "string", "pattern": IDENTIFIER}
            elif key in ("sha256", "base_snapshot"):
                properties[key] = {"type": "string", "pattern": SHA256}
        if "implementation_id" in properties:
            properties["implementation_id"] = _enum(
                properties["implementation_id"], permitted_implementations
            )
        for key, value in (("candidate_id", candidate_id), ("evaluation_id", evaluation_id)):
            if key in properties and value is not None:
                properties[key] = {**properties[key], "const": value}
        if "evidence_ids" in properties:
            properties["evidence_ids"] = evidence_items()
            if name in ("CandidateBrief", "ReviewFindings", "Finding", "SourceDraft"):
                properties["evidence_ids"]["minItems"] = 1
        if name == "CandidateBrief":
            properties["eligibility_gaps"]["description"] = (
                "List unmet prerequisites for forming this proposal. Declared calibration, "
                "candidate evaluation, scientific checks, acceptance and confirmation happen "
                "after proposal. Their absence alone is not a proposal prerequisite gap. "
                "State untested scientific expectations in expected_tradeoffs and preserve "
                "genuinely missing source or interface prerequisites here."
            )
        if name == "Finding":
            properties["supporting_checks"]["minItems"] = 1
            properties["supporting_checks"]["description"] = (
                "Copy exact check.name strings from the checks of evaluation_id in the granted "
                "evidence. Do not include evaluation IDs, versions, statuses or explanations "
                "in these strings. Put explanations in description."
            )
        if name == "ArtifactRef":
            properties["size_bytes"]["minimum"] = 0
        if name == "ReviewFindings":
            definition["allOf"] = [
                {
                    "if": {"properties": {"recommendation": {"const": "proceed"}}},
                    "then": {
                        "properties": {
                            "missing_evidence": {"maxItems": 0},
                            "findings": {
                                "items": {
                                    "properties": {
                                        "severity": {"enum": ["advisory", "information"]}
                                    }
                                }
                            },
                        }
                    },
                }
            ]
        if name == "ImplementationBundle":
            properties["admitted_identity"] = {"const": None}
            properties["sources"]["minItems"] = 1
        if name == "SourceDraft":
            properties["files"] = {
                "type": "object",
                "additionalProperties": False,
                "properties": {"adapter.py": {"type": "string", "pattern": r"\S"}},
                "required": ["adapter.py"],
            }
            properties["dependencies"] = {"const": ["python-stdlib", "math"]}
    variants = []
    for kind in outputs:
        if kind is NextStep:
            for action in ("assign", "freeze", "stop"):
                if action not in task.allowed_operations:
                    continue
                role = (
                    {"enum": ["investigator", "implementer", "reviewer"]}
                    if action == "assign"
                    else {"const": None}
                )
                variants.append(
                    {
                        "properties": {
                            "output": {
                                "allOf": [
                                    schema.annotation(kind),
                                    {"properties": {"action": {"const": action}, "role": role}},
                                ]
                            },
                            "proposed_next_action": {"const": action},
                        }
                    }
                )
        else:
            action = {
                CandidateBrief: "propose",
                SuppliedConfiguration: "configure",
                ReviewFindings: "review",
                SourceDraft: "configure",
                ImplementationBundle: "configure",
            }[kind]
            allowed = [v for v in (action, "stop") if v in task.allowed_operations]
            if task.role == SINGLE_ROLE:
                allowed = [v for v in allowed if v == action]
            if allowed:
                variants.append(
                    {
                        "properties": {
                            "output": schema.annotation(kind),
                            "proposed_next_action": _enum({}, allowed),
                        }
                    }
                )
    if variants:
        root["oneOf"] = variants
    else:
        root["not"] = {}
    root["allOf"] = [
        {
            "if": {"properties": {"status": {"const": "complete"}}},
            "then": {"properties": {"unresolved_issues": {"maxItems": 0}}},
        }
    ]
    root["$defs"] = schema.definitions
    document = {
        "version": VERSION,
        "schema": root,
        "instructions": [
            "Return one JSON handoff object with these exact field names and types. Do not add keys.",
            "For a native transport, serialize this handoff into its outer handoff_json string.",
            "Use only the permitted action and output appropriate to the current question and scientific phase.",
            "Cite only granted evidence. Every output evidence ID must also appear in supporting_artifact_ids.",
            "Propose and configure only supplied catalogue starting/fixed parameters. Only the trusted controller performs declared calibration. Do not invent candidate, check or source provenance.",
            "When comparison_policy supplies next_proposal_candidate_id, propose that exact candidate. Baseline evaluation does not consume a candidate proposal from the ordered pool.",
            "Review findings must cite checks in the granted evaluation. Blocking or missing evidence cannot recommend proceed.",
            "For calibrated evaluations, review the evaluated configuration and calibration study linkage, not just catalogue starting parameters.",
            "In an evaluated-candidate review, trusted acceptance and any configured confirmation occur downstream. Pending downstream gates alone are not missing pre-review prerequisites. Keep genuine identity or check gaps blocking and report scientific limitations without claiming later gates passed.",
            "Source drafts have only adapter.py and the fixed dependencies. They claim no executed checks or admission.",
            "The strict record parser, exact grants, phase/candidate/evaluation checks and scientific rules remain authoritative.",
            "This schema grants no tools, workspace, data access, admission or additional budget.",
        ],
        "max_handoff_bytes": 65536,
    }
    if len(canonical_json(document).encode()) > MAX_BYTES:
        raise ValueError("model-visible output contract exceeds its 32 KiB allowance")
    return document
