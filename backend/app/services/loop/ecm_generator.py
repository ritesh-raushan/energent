import json
import logging

from pydantic import BaseModel

from app.services.analysis.models import AnalysisResult
from app.services.llm.models import LLMMessage
from app.services.llm.openrouter import OpenRouterProvider
from app.services.loop.idf_parser import IDFData

logger = logging.getLogger(__name__)


class ECMResult(BaseModel):
    heating_occupied_c: float
    cooling_occupied_c: float
    reasoning: str
    estimated_savings_pct: float


def generate_ecms(
    idf_data: IDFData,
    analysis: AnalysisResult,
) -> ECMResult:
    provider = OpenRouterProvider()
    if not provider.is_available():
        return _rule_based_ecms(idf_data, analysis)

    messages = _build_ecm_prompt(idf_data, analysis)
    try:
        response = provider.chat(messages, temperature=0.3)
        return _parse_ecm_response(response.content, idf_data)
    except Exception as e:
        logger.warning("LLM ECM generation failed, falling back to rules: %s", e)
        return _rule_based_ecms(idf_data, analysis)


def _build_ecm_prompt(idf_data: IDFData, analysis: AnalysisResult) -> list[LLMMessage]:
    system_prompt = """You are an expert building energy engineer. You generate Energy Conservation Measures (ECMs)
by suggesting optimal thermostat setpoints for commercial buildings.

You must respond with ONLY valid JSON in this exact format:
{
    "heating_occupied_c": 21.0,
    "cooling_occupied_c": 24.0,
    "reasoning": "Explanation of why these setpoints will save energy while maintaining comfort",
    "estimated_savings_pct": 5.0
}

Rules:
- Heating occupied setpoint should be between 18-22°C (lower = more savings)
- Cooling occupied setpoint should be between 23-26°C (higher = more savings)
- Consider the current energy breakdown and recommendations
- Balance energy savings with occupant comfort"""

    user_prompt = f"""Current building configuration:
- Heating occupied setpoint: {idf_data.heating_occupied_c}°C
- Heating unoccupied setpoint: {idf_data.heating_unoccupied_c}°C
- Cooling occupied setpoint: {idf_data.cooling_occupied_c}°C
- Cooling unoccupied setpoint: {idf_data.cooling_unoccupied_c}°C

Energy analysis:
- Total electricity: {analysis.energy_breakdown.total_electricity_kwh} kWh
- Heating: {analysis.energy_breakdown.heating_pct}%
- Cooling: {analysis.energy_breakdown.cooling_pct}%
- Fans: {analysis.energy_breakdown.fans_pct}%
- Average zone temperature: {analysis.hvac_summary.avg_zone_temp_c}°C
- Peak load: {analysis.peak_load.peak_kw} kW

Recommendations:
{json.dumps([{"title": r.title, "description": r.description} for r in analysis.recommendations], indent=2)}

Suggest optimal setpoints that will reduce energy consumption while maintaining thermal comfort."""

    return [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]


def _parse_ecm_response(content: str, idf_data: IDFData) -> ECMResult:
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())
        return ECMResult(
            heating_occupied_c=float(data.get("heating_occupied_c", idf_data.heating_occupied_c)),
            cooling_occupied_c=float(data.get("cooling_occupied_c", idf_data.cooling_occupied_c)),
            reasoning=data.get("reasoning", ""),
            estimated_savings_pct=float(data.get("estimated_savings_pct", 0.0)),
        )
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse ECM response: %s", e)
        return _rule_based_ecms(idf_data, AnalysisResult())


def _rule_based_ecms(idf_data: IDFData, analysis: AnalysisResult) -> ECMResult:
    heating = idf_data.heating_occupied_c
    cooling = idf_data.cooling_occupied_c

    if analysis.energy_breakdown.heating_pct > 30:
        heating = max(19.0, heating - 1.0)
    if analysis.energy_breakdown.cooling_pct > 25:
        cooling = min(25.0, cooling + 1.0)

    if analysis.hvac_summary.avg_zone_temp_c > 24.0:
        cooling = min(25.0, cooling + 0.5)
    elif analysis.hvac_summary.avg_zone_temp_c < 20.0:
        heating = max(19.0, heating - 0.5)

    savings = 0.0
    if heating < idf_data.heating_occupied_c:
        savings += (idf_data.heating_occupied_c - heating) * 2.0
    if cooling > idf_data.cooling_occupied_c:
        savings += (cooling - idf_data.cooling_occupied_c) * 1.5

    return ECMResult(
        heating_occupied_c=heating,
        cooling_occupied_c=cooling,
        reasoning=f"Rule-based: Adjusted heating from {idf_data.heating_occupied_c}°C to {heating}°C and cooling from {idf_data.cooling_occupied_c}°C to {cooling}°C based on energy breakdown and comfort analysis.",
        estimated_savings_pct=round(savings, 1),
    )
