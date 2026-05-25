import json
import re
import logging
from app.ai.schemas import EvalResult
from app.scalping.models.supervisor import SupervisorDecision

logger = logging.getLogger(__name__)

_VALID_VERDICTS = {"PROMOTE", "HOLD", "DEMOTE"}
_VALID_ACTIONS = {"update_params", "change_strategy", "pause_trading", "resume_trading", "no_action"}
_MD_JSON_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


class EvalParseError(Exception):
    pass


def parse_eval_result(raw: str, strategy_id: str, model_used: str) -> EvalResult:
    # Estrai JSON da markdown se presente
    md_match = _MD_JSON_RE.search(raw)
    json_str = md_match.group(1).strip() if md_match else raw.strip()

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise EvalParseError(f"JSON non valido: {e}") from e

    # Verdict
    verdict = data.get("verdict", "")
    if verdict not in _VALID_VERDICTS:
        raise EvalParseError(f"verdict non valido: '{verdict}'. Attesi: {_VALID_VERDICTS}")

    # Reasoning
    reasoning = data.get("reasoning", "")
    if not reasoning or not reasoning.strip():
        raise EvalParseError("reasoning mancante o vuoto")

    # Score clamp
    score = float(data.get("score", 0.0))
    if score > 1.0 or score < 0.0:
        logger.warning(f"Score {score} fuori range [0,1], clampato")
        score = max(0.0, min(1.0, score))

    confidence = float(data.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))

    return EvalResult(
        strategy_id=strategy_id,
        score=score,
        verdict=verdict,
        reasoning=reasoning.strip(),
        confidence=confidence,
        model_used=model_used,
        tokens_used=data.get("tokens_used", 0),
    )


def parse_supervisor_decision(raw: str) -> SupervisorDecision:
    """Parse AI supervisor decision JSON with new fields."""
    md_match = _MD_JSON_RE.search(raw)
    json_str = md_match.group(1).strip() if md_match else raw.strip()

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise EvalParseError(f"JSON supervisor non valido: {e}") from e

    action = data.get("action", "")
    if action not in _VALID_ACTIONS:
        raise EvalParseError(f"action non valida: '{action}'. Attese: {_VALID_ACTIONS}")

    return SupervisorDecision(
        action=action,
        reason=data.get("reason", ""),
        confidence=float(data.get("confidence", 0.5)),
        market_bias=data.get("market_bias"),
        primary_signal=data.get("primary_signal"),
        new_params=data.get("new_params"),
        new_strategy=data.get("new_strategy"),
    )
