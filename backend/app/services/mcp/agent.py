import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.config import settings
from app.services.llm.models import LLMMessage, LLMResponse
from app.services.llm.openrouter import OpenRouterProvider
from app.services.mcp.tools import get_tool_definitions

logger = logging.getLogger(__name__)


class AgentStep(BaseModel):
    iteration: int
    round: int = 1
    tool: str
    arguments: dict
    result: dict


class RoundSummary(BaseModel):
    round_number: int
    energy_savings_kwh: float = 0.0
    energy_savings_pct: float = 0.0
    pmv_change: float = 0.0
    ppd_change: float = 0.0
    ecm: dict | None = None
    baseline_analysis: dict | None = None
    optimized_analysis: dict | None = None


class AgentResult(BaseModel):
    steps: list[AgentStep] = []
    rounds: list[RoundSummary] = []
    final_result: dict | None = None
    success: bool = False
    converged: bool = False
    convergence_reason: str | None = None
    error: str | None = None


class IterativeAgent:
    def __init__(self, max_rounds: int = 5):
        self.provider = OpenRouterProvider()
        self.tools = {t.name: t for t in get_tool_definitions()}
        self.max_rounds = max_rounds
        self.current_idf_path = None
        self.output_dir = None

    def run(self, objective: str, context: dict | None = None) -> AgentResult:
        result = AgentResult()
        context = context or {}
        self.output_dir = context.get("output_dir", "/mnt/c/EnergentOutput")
        self.current_idf_path = context.get(
            "idf_path", "/home/riteshwsl/projects/energent/simulation/idf/RefBldgSmallOfficeNew2004_Chicago.idf"
        )
        weather_path = context.get(
            "weather_path", "/home/riteshwsl/projects/energent/simulation/weather/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"
        )

        round_number = 1
        total_iteration = 0
        previous_round = None

        for round_number in range(1, self.max_rounds + 1):
            logger.info("Starting optimization round %d/%d", round_number, self.max_rounds)

            round_summary = RoundSummary(round_number=round_number)
            round_steps = []

            # Full optimization cycle for this round
            round_data = self._run_optimization_round(
                round_number=round_number,
                weather_path=weather_path,
                previous_round=previous_round,
                result=result,
            )

            if not round_data:
                logger.warning("Round %d failed, stopping", round_number)
                break

            round_summary.ecm = round_data.get("ecm")
            round_summary.baseline_analysis = round_data.get("baseline_analysis")
            round_summary.optimized_analysis = round_data.get("optimized_analysis")

            # Calculate savings
            base = round_data.get("baseline_analysis", {})
            opt = round_data.get("optimized_analysis", {})
            base_kwh = base.get("energy_breakdown", {}).get("total_electricity_kwh", 0)
            opt_kwh = opt.get("energy_breakdown", {}).get("total_electricity_kwh", 0)
            round_summary.energy_savings_kwh = round(base_kwh - opt_kwh, 2)
            round_summary.energy_savings_pct = round((base_kwh - opt_kwh) / base_kwh * 100, 1) if base_kwh > 0 else 0

            base_pmv = base.get("thermal_comfort", {}).get("pmv", 0)
            opt_pmv = opt.get("thermal_comfort", {}).get("pmv", 0)
            round_summary.pmv_change = round(opt_pmv - base_pmv, 2)

            base_ppd = base.get("thermal_comfort", {}).get("ppd", 5)
            opt_ppd = opt.get("thermal_comfort", {}).get("ppd", 5)
            round_summary.ppd_change = round(opt_ppd - base_ppd, 1)

            result.rounds.append(round_summary)

            # Check convergence
            converged, reason = self._check_convergence(result.rounds)
            if converged:
                result.converged = True
                result.convergence_reason = reason
                logger.info("Converged after round %d: %s", round_number, reason)
                break

            previous_round = round_summary
            self.current_idf_path = round_data.get("modified_idf_path")

        # Build final result
        result.success = True
        result.final_result = self._build_final_result(result.rounds)
        return result

    def _run_optimization_round(
        self,
        round_number: int,
        weather_path: str,
        previous_round: RoundSummary | None,
        result: AgentResult,
    ) -> dict | None:
        """Run a complete optimization cycle: parse -> simulate -> analyze -> ecm -> modify -> simulate -> analyze"""
        round_steps = []

        # Step 1: parse_idf
        step_result = self._execute_tool(
            "parse_idf",
            {"idf_path": self.current_idf_path},
            round_number,
            len(result.steps) + 1,
        )
        round_steps.append(step_result)
        result.steps.append(step_result)

        # Step 2: run_simulation (baseline)
        sim_result = self._execute_tool(
            "run_simulation",
            {
                "idf_path": self.current_idf_path,
                "weather_path": weather_path,
                "output_dir": self.output_dir,
            },
            round_number,
            len(result.steps) + 1,
        )
        round_steps.append(sim_result)
        result.steps.append(sim_result)

        if not sim_result.result.get("success"):
            return None

        csv_path = sim_result.result.get("csv_path")

        # Step 3: analyze_results (baseline)
        base_analysis = self._execute_tool(
            "analyze_results",
            {"csv_path": csv_path},
            round_number,
            len(result.steps) + 1,
        )
        round_steps.append(base_analysis)
        result.steps.append(base_analysis)

        # Step 4: generate_ecms
        ecm_result = self._execute_tool(
            "generate_ecms",
            {"analysis": base_analysis.result},
            round_number,
            len(result.steps) + 1,
        )
        round_steps.append(ecm_result)
        result.steps.append(ecm_result)

        if not ecm_result.result.get("success"):
            return None

        # Step 5: modify_setpoints
        modified_idf = f"{self.output_dir}/modified_round{round_number}.idf"
        modify_result = self._execute_tool(
            "modify_setpoints",
            {
                "idf_path": self.current_idf_path,
                "output_path": modified_idf,
                "heating_occupied_c": ecm_result.result.get("heating_occupied_c"),
                "cooling_occupied_c": ecm_result.result.get("cooling_occupied_c"),
            },
            round_number,
            len(result.steps) + 1,
        )
        round_steps.append(modify_result)
        result.steps.append(modify_result)

        if not modify_result.result.get("success"):
            return None

        # Step 6: run_simulation (optimized)
        opt_sim_result = self._execute_tool(
            "run_simulation",
            {
                "idf_path": modified_idf,
                "weather_path": weather_path,
                "output_dir": self.output_dir,
            },
            round_number,
            len(result.steps) + 1,
        )
        round_steps.append(opt_sim_result)
        result.steps.append(opt_sim_result)

        if not opt_sim_result.result.get("success"):
            return None

        opt_csv = opt_sim_result.result.get("csv_path")

        # Step 7: analyze_results (optimized)
        opt_analysis = self._execute_tool(
            "analyze_results",
            {"csv_path": opt_csv},
            round_number,
            len(result.steps) + 1,
        )
        round_steps.append(opt_analysis)
        result.steps.append(opt_analysis)

        # Save modified IDF to repo
        self._save_modified_idf(modified_idf, round_number)

        return {
            "ecm": ecm_result.result,
            "baseline_analysis": base_analysis.result,
            "optimized_analysis": opt_analysis.result,
            "modified_idf_path": modified_idf,
        }

    def _execute_tool(
        self,
        tool_name: str,
        args: dict,
        round_number: int,
        iteration: int,
    ) -> AgentStep:
        tool = self.tools.get(tool_name)
        if not tool:
            tool_result = {"error": f"Unknown tool: {tool_name}", "success": False}
        else:
            try:
                tool_result = tool.handler(**args)
            except Exception as e:
                logger.error("Tool %s failed: %s", tool_name, e)
                tool_result = {"error": str(e), "success": False}

        return AgentStep(
            iteration=iteration,
            round=round_number,
            tool=tool_name,
            arguments=args,
            result=tool_result,
        )

    def _check_convergence(self, rounds: list[RoundSummary]) -> tuple[bool, str]:
        if len(rounds) < 2:
            return False, ""

        last = rounds[-1]
        prev = rounds[-2]

        # Energy savings plateau (less than 1% additional savings)
        if last.energy_savings_pct < 1.0 and abs(last.energy_savings_pct - prev.energy_savings_pct) < 0.5:
            return True, f"Energy savings plateaued at {last.energy_savings_pct:.1f}%"

        # PMV within comfort band (-0.5 to 0.5) and PPD < 10%
        opt = last.optimized_analysis
        if opt:
            pmv = opt.get("thermal_comfort", {}).get("pmv", 99)
            ppd = opt.get("thermal_comfort", {}).get("ppd", 99)
            if abs(pmv) <= 0.5 and ppd <= 10:
                return True, f"Comfort achieved: PMV={pmv:.2f}, PPD={ppd:.1f}%"

        # Max rounds reached
        if len(rounds) >= self.max_rounds:
            return True, f"Max rounds ({self.max_rounds}) reached"

        return False, ""

    def _save_modified_idf(self, modified_idf: str, round_number: int):
        """Copy modified IDF to simulation/idf/modified/ for version control"""
        try:
            repo_dir = Path("/home/riteshwsl/projects/energent/simulation/idf/modified")
            repo_dir.mkdir(parents=True, exist_ok=True)
            dest = repo_dir / f"RefBldgSmallOfficeNew2004_Chicago_round{round_number}.idf"
            import shutil
            shutil.copy2(modified_idf, dest)
            logger.info("Saved modified IDF to %s", dest)
        except Exception as e:
            logger.warning("Failed to save modified IDF to repo: %s", e)

    def _build_final_result(self, rounds: list[RoundSummary]) -> dict:
        if not rounds:
            return {}

        last = rounds[-1]
        total_savings = sum(r.energy_savings_kwh for r in rounds)
        total_savings_pct = sum(r.energy_savings_pct for r in rounds)

        return {
            "total_rounds": len(rounds),
            "converged": True if rounds else False,
            "convergence_reason": last.convergence_reason if hasattr(last, 'convergence_reason') else "Completed",
            "total_energy_savings_kwh": round(total_savings, 2),
            "total_energy_savings_pct": round(total_savings_pct, 1),
            "final_pmv": last.optimized_analysis.get("thermal_comfort", {}).get("pmv") if last.optimized_analysis else None,
            "final_ppd": last.optimized_analysis.get("thermal_comfort", {}).get("ppd") if last.optimized_analysis else None,
            "rounds_summary": [
                {
                    "round": r.round_number,
                    "savings_kwh": r.energy_savings_kwh,
                    "savings_pct": r.energy_savings_pct,
                    "heating_setpoint_c": r.ecm.get("heating_occupied_c") if r.ecm else None,
                    "cooling_setpoint_c": r.ecm.get("cooling_occupied_c") if r.ecm else None,
                }
                for r in rounds
            ],
        }


def run_iterative_agent(
    objective: str,
    context: dict | None = None,
    max_rounds: int = 5,
) -> AgentResult:
    agent = IterativeAgent(max_rounds=max_rounds)
    return agent.run(objective, context)