import json

from app.services.analysis.models import AnalysisResult
from app.services.llm.models import LLMMessage


def build_analysis_prompt(analysis: AnalysisResult) -> list[LLMMessage]:
    summary_data = {
        "energy_breakdown": analysis.energy_breakdown.model_dump(),
        "peak_load": analysis.peak_load.model_dump(),
        "hvac_summary": analysis.hvac_summary.model_dump(),
        "overall_score": analysis.overall_score,
        "total_potential_savings_kwh": analysis.total_potential_savings_kwh,
    }

    recommendations_data = [
        {
            "category": r.category,
            "priority": r.priority,
            "title": r.title,
            "description": r.description,
            "estimated_savings_kwh": r.estimated_savings_kwh,
        }
        for r in analysis.recommendations
    ]

    system_prompt = """You are an expert building energy analyst AI. You analyze EnergyPlus simulation data
and provide refined, actionable energy optimization recommendations for commercial buildings.

Your recommendations must be:
1. Specific and actionable (not generic advice)
2. Based on the actual data provided
3. Prioritized by potential energy savings
4. Include concrete implementation steps
5. Consider both energy savings and occupant comfort

Always respond in valid JSON format."""

    user_prompt = f"""Analyze the following building energy simulation results and provide refined recommendations:

## Simulation Data
{json.dumps(summary_data, indent=2)}

## Rule-Based Recommendations
{json.dumps(recommendations_data, indent=2)}

## Instructions
1. Review the rule-based recommendations and refine them with more specific details
2. Add any additional insights the data suggests
3. Provide an overall assessment of the building's energy performance
4. Suggest the top 3-5 most impactful actions with estimated savings

Respond with JSON in this exact format:
{{
  "summary": "Brief overall assessment (2-3 sentences)",
  "refined_recommendations": [
    {{
      "original_title": "Original rule-based title",
      "refined_title": "More specific refined title",
      "refined_description": "Detailed actionable description with specific steps",
      "priority": "high/medium/low",
      "category": "HVAC/Lighting/Load Management/etc",
      "action_items": ["Step 1", "Step 2", "Step 3"],
      "estimated_impact": "Description of expected impact"
    }}
  ],
  "additional_insights": ["Insight 1", "Insight 2"]
}}"""

    return [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]


def build_refinement_prompt(
    analysis: AnalysisResult,
    question: str,
) -> list[LLMMessage]:
    summary_data = {
        "energy_breakdown": analysis.energy_breakdown.model_dump(),
        "peak_load": analysis.peak_load.model_dump(),
        "hvac_summary": analysis.hvac_summary.model_dump(),
        "overall_score": analysis.overall_score,
    }

    system_prompt = """You are an expert building energy analyst AI. You answer questions about
building energy simulation data and provide specific, actionable advice.

Be concise but thorough. Reference the actual data when making recommendations."""

    user_prompt = f"""Building energy simulation data:
{json.dumps(summary_data, indent=2)}

Existing recommendations:
{json.dumps([{"title": r.title, "description": r.description, "priority": r.priority} for r in analysis.recommendations], indent=2)}

Question: {question}"""

    return [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]
