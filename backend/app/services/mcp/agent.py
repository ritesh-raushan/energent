import json
import logging
from typing import Any

from pydantic import BaseModel

from app.config import settings
from app.services.llm.models import LLMMessage, LLMResponse
from app.services.llm.openrouter import OpenRouterProvider
from app.services.mcp.tools import get_tool_definitions

logger = logging.getLogger(__name__)


class AgentStep(BaseModel):
    iteration: int
    tool: str
    arguments: dict
    result: dict


class AgentResult(BaseModel):
    steps: list[AgentStep] = []
    final_result: dict | None = None
    success: bool = False
    error: str | None = None


class Agent:
    def __init__(self, max_iterations: int = 10):
        self.provider = OpenRouterProvider()
        self.tools = {t.name: t for t in get_tool_definitions()}
        self.max_iterations = max_iterations

    def run(self, objective: str, context: dict | None = None) -> AgentResult:
        result = AgentResult()
        context = context or {}

        messages: list[LLMMessage] = [
            LLMMessage(role="system", content=self._get_system_prompt()),
            LLMMessage(role="user", content=self._get_user_prompt(objective, context)),
        ]

        for iteration in range(self.max_iterations):
            logger.info("Agent iteration %d/%d", iteration + 1, self.max_iterations)

            tool_defs = [t.to_openai_format() for t in self.tools.values()]
            response = self.provider.chat(
                messages=messages,
                tools=tool_defs,
                tool_choice="auto",
            )

            if response.tool_calls:
                # Add assistant message with tool_calls first
                messages.append(LLMMessage(
                    role="assistant",
                    content="",
                    tool_calls=response.tool_calls,
                ))

                for tool_call in response.tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])

                    if tool_name not in self.tools:
                        tool_result = {"error": f"Unknown tool: {tool_name}"}
                    else:
                        try:
                            tool_result = self.tools[tool_name].handler(**tool_args)
                        except Exception as e:
                            logger.error("Tool %s failed: %s", tool_name, e)
                            tool_result = {"error": str(e)}

                    result.steps.append(AgentStep(
                        iteration=iteration + 1,
                        tool=tool_name,
                        arguments=tool_args,
                        result=tool_result,
                    ))

                    messages.append(LLMMessage(
                        role="tool",
                        content=json.dumps(tool_result),
                        tool_call_id=tool_call["id"],
                    ))
            else:
                result.final_result = {"summary": response.content}
                result.success = True
                logger.info("Agent completed after %d iterations", iteration + 1)
                break
        else:
            result.error = "Max iterations reached"
            result.success = False
            logger.warning("Agent max iterations reached")

        return result

    def _get_system_prompt(self) -> str:
        return """You are an autonomous building energy optimization agent. Your goal is to minimize energy consumption while maintaining thermal comfort (PMV between -0.5 and +0.5, PPD < 10%).

Available tools:
1. parse_idf - Read thermostat setpoints from an IDF file
2. run_simulation - Execute EnergyPlus simulation
3. analyze_results - Parse CSV output and compute energy/comfort metrics
4. modify_setpoints - Change heating/cooling setpoints in an IDF file
5. generate_ecms - Get optimal setpoints based on analysis
6. get_errors - Check EnergyPlus error/warning files

Workflow for closed-loop optimization:
1. Parse the baseline IDF to understand current setpoints
2. Run baseline simulation
3. Analyze results (energy breakdown, PMV/PPD, peak load)
4. Generate ECMs (optimal setpoints) based on analysis
5. Modify IDF with new setpoints
6. Run optimized simulation
7. Analyze optimized results
8. Compare baseline vs optimized - report energy savings and comfort impact

Stop when you have completed a full optimization cycle and reported the comparison.
Always output tool calls in the correct JSON format."""

    def _get_user_prompt(self, objective: str, context: dict) -> str:
        return f"""Objective: {objective}

Context:
- IDF file: {context.get('idf_path', 'simulation/idf/RefBldgSmallOfficeNew2004_Chicago.idf')}
- Weather file: {context.get('weather_path', 'simulation/weather/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw')}
- Output directory: {context.get('output_dir', '/mnt/c/EnergentOutput')}

Execute the full closed-loop optimization cycle. Report final energy savings (kWh and %) and thermal comfort (PMV/PPD) comparison."""


def run_agent(objective: str, context: dict | None = None) -> AgentResult:
    agent = Agent()
    return agent.run(objective, context)