"""Provider decoding hints, not Cognova's acceptance or business contract."""

from typing import Any

from app.academic_intelligence.gemini_schemas import PlanProposal


def plan_generation_schema() -> dict[str, Any]:
    """Inline local definitions and keep only structural decoding constraints.

    Array bounds and date-time matchers multiply constrained-decoder states,
    especially challenges -> evidence. Lengths, dates, and all business rules
    remain enforced locally. Do not use this schema to accept a proposal.
    """
    source = PlanProposal.model_json_schema()
    definitions = source.get("$defs", {})

    def project(node: dict[str, Any]) -> dict[str, Any]:
        if "$ref" in node:
            ref = node["$ref"]
            prefix = "#/$defs/"
            if not ref.startswith(prefix):
                raise ValueError("Only local plan definitions are supported")
            return project(definitions[ref[len(prefix):]])
        result = {
            key: node[key]
            for key in ("type", "enum", "required", "additionalProperties")
            if key in node
        }
        if "properties" in node:
            result["properties"] = {
                name: project(child) for name, child in node["properties"].items()
            }
        if "items" in node:
            result["items"] = project(node["items"])
        if "anyOf" in node:
            # The internal plan only uses scalar-or-null unions. Fail closed if
            # that contract evolves instead of silently dropping a branch.
            branches = [project(child) for child in node["anyOf"]]
            if any(set(branch) != {"type"} for branch in branches):
                raise ValueError("Unsupported plan union")
            result["type"] = [branch["type"] for branch in branches]
        return result

    return project(source)


def decode_plan_proposal(payload: str) -> PlanProposal:
    """Identity mapping: original defaults only, no coercion or output repair."""
    return PlanProposal.model_validate_json(payload, strict=True)
