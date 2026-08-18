from __future__ import annotations

VALID_ANALYZER_POLICIES = {"off", "safe", "strict", "lab"}
RUNTIME_ANALYZER_POLICIES = VALID_ANALYZER_POLICIES - {"off"}


class AnalyzerPolicyConfigError(ValueError):
    pass


def normalize_runtime_policy(policy: str, field_name: str) -> str:
    value = (policy or "").strip().lower()
    if value not in RUNTIME_ANALYZER_POLICIES:
        allowed = ", ".join(sorted(RUNTIME_ANALYZER_POLICIES))
        raise AnalyzerPolicyConfigError(
            f"Invalid {field_name}: '{policy}'. Expected one of: {allowed}"
        )
    return value


def parse_policy_map(
    mapping_text: str, default_policy: str
) -> tuple[dict[int, str], str]:
    explicit: dict[int, str] = {}
    wildcard_policy = normalize_runtime_policy(
        default_policy, "analyzer default policy"
    )

    text = (mapping_text or "").strip()
    if not text:
        return explicit, wildcard_policy

    for raw_item in text.split(","):
        item = raw_item.strip()
        if not item:
            continue
        if ":" not in item:
            raise AnalyzerPolicyConfigError(
                f"Invalid analyzer policy map item: '{item}'. Expected format <program_id>:<policy> or *:<policy>"
            )

        key_text, value_text = item.split(":", 1)
        key = key_text.strip()
        value = normalize_runtime_policy(
            value_text.strip(), f"analyzer policy for '{key or raw_item}'"
        )

        if key == "*":
            wildcard_policy = value
            continue

        try:
            program_id = int(key)
        except ValueError as exc:
            raise AnalyzerPolicyConfigError(
                f"Invalid analyzer policy map key: '{key}'. Expected integer program id or '*'"
            ) from exc

        explicit[program_id] = value

    return explicit, wildcard_policy


def resolve_policy(mapping_text: str, default_policy: str, program_id: int) -> str:
    explicit, wildcard_policy = parse_policy_map(mapping_text, default_policy)
    return explicit.get(program_id, wildcard_policy)
