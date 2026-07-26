import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.analysis.engine import analyze
from app.services.analysis.models import AnalysisResult
from app.services.energyplus.parser import parse_csv
from app.services.llm.models import LLMAnalysisResult, RefinedRecommendation
from app.services.llm.openrouter import OpenRouterProvider
from app.services.llm.prompt import build_analysis_prompt, build_refinement_prompt

logger = logging.getLogger(__name__)

router = APIRouter(tags=["llm"])


class RefineRequest(BaseModel):
    analysis: AnalysisResult
    question: str = ""


def _get_provider() -> OpenRouterProvider:
    provider = OpenRouterProvider()
    if not provider.is_available():
        raise HTTPException(
            status_code=503,
            detail="LLM provider not configured. Set OPENROUTER_API_KEY in .env",
        )
    return provider


def _parse_llm_response(content: str) -> dict:
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        return json.loads(content.strip())
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM response as JSON, using raw content")
        return {"summary": content, "refined_recommendations": [], "additional_insights": []}


@router.post("/llm/refine")
def refine_recommendations(request: RefineRequest) -> dict:
    provider = _get_provider()

    messages = build_analysis_prompt(request.analysis)

    try:
        response = provider.chat(messages, temperature=0.7)
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

    parsed = _parse_llm_response(response.content)

    refined_recs = []
    for rec in parsed.get("refined_recommendations", []):
        refined_recs.append(RefinedRecommendation(
            original_title=rec.get("original_title", ""),
            refined_title=rec.get("refined_title", rec.get("original_title", "")),
            refined_description=rec.get("refined_description", rec.get("description", "")),
            priority=rec.get("priority", "medium"),
            category=rec.get("category", "General"),
            action_items=rec.get("action_items", []),
            estimated_impact=rec.get("estimated_impact", ""),
        ))

    return {
        "status": "success",
        "result": LLMAnalysisResult(
            summary=parsed.get("summary", ""),
            refined_recommendations=refined_recs,
            additional_insights=parsed.get("additional_insights", []),
            model_used=response.model,
        ).model_dump(),
    }


@router.post("/llm/ask")
def ask_about_building(request: RefineRequest) -> dict:
    provider = _get_provider()

    messages = build_refinement_prompt(request.analysis, request.question)

    try:
        response = provider.chat(messages, temperature=0.7)
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

    return {
        "status": "success",
        "answer": response.content,
        "model_used": response.model,
    }


@router.get("/llm/health")
def llm_health() -> dict:
    provider = OpenRouterProvider()
    return {
        "configured": provider.is_available(),
        "model": provider.model,
    }
