from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: str
    content: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict] | None = None


class LLMResponse(BaseModel):
    content: str = ""
    model: str = ""
    usage: dict = Field(default_factory=dict)
    tool_calls: list[dict] | None = None


class RefinedRecommendation(BaseModel):
    original_title: str
    refined_title: str
    refined_description: str
    priority: str
    category: str
    action_items: list[str] = Field(default_factory=list)
    estimated_impact: str = ""


class LLMAnalysisResult(BaseModel):
    summary: str
    refined_recommendations: list[RefinedRecommendation] = Field(default_factory=list)
    additional_insights: list[str] = Field(default_factory=list)
    model_used: str = ""
