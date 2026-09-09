import asyncio
import operator
import os
import random
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, TypedDict

from pydantic import BaseModel

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from core.config import get_settings, DATA_DIR
from core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class ResumeOutput(BaseModel):
    ATS_score: int
    jd_keywords: list[str]
    resume_keywords: list[str]
    matched_keywords: list[str]
    unmatched_keywords: list[str]
    suggested_point_rewrites: list[str]
    updated_resume: str


@dataclass
class ResumeOptimizer_deps:
    words_to_avoid: list[str]
    ATS_pass_score: int
    formatting_reqs: list[str]


class AgentState(TypedDict):
    history: Annotated[list[str], operator.add]
    init_resume_keywords: list[str]
    resume_content: str
    jd_content: str
    processing_step: str
    final_resume: str
    jd_keywords: list[str]
    resume_keywords: list[str]
    ats_score: float
    matched_keywords: list[str]
    unmatched_keywords: list[str]
    iteration: int
    resume_path: str
    jd_path: str


system_instructions = """You are an expert ATS (Applicant Tracking System) resume optimizer specializing in software engineering roles.

Your core capabilities:
1. KEYWORD EXTRACTION: You identify technical skills, tools, frameworks, methodologies, soft skills, and domain-specific terms from both resumes and job descriptions. Include variations (e.g., "React" and "React.js" count as the same keyword).
2. KEYWORD MATCHING: When comparing keywords, treat semantically equivalent terms as matches (e.g., "CI/CD" matches "continuous integration", "JS" matches "JavaScript", "REST APIs" matches "RESTful APIs").
3. ATS SCORING: Score resumes 0-100 based on keyword coverage, formatting compliance, quantified achievements, and relevance to the target JD. A passing score is {ATS_pass_score}.
4. RESUME REWRITING: When rewriting bullet points, you MUST:
   - Preserve all company names, job titles, dates, and locations exactly as they appear
   - Keep quantified metrics (percentages, numbers, timeframes) intact
   - Incorporate missing JD keywords naturally into existing bullet points
   - Use strong action verbs (Developed, Architected, Optimized, Led, Implemented)
   - Keep each bullet point concise (1-2 lines max)
   - Never fabricate achievements or metrics not present in the original
   - Don't add irrelevant job information directly into resume. Keep the resume experience and technologies very similar to what it was before and incorporate or reword the resume to have those keywords

WORDS TO AVOID (never use these in rewritten bullets):
{words_to_avoid}

FORMATTING REQUIREMENTS:
{formatting_reqs}

OUTPUT RULES:
- Always populate ALL fields in the output schema
- For fields not applicable to the current task, use empty lists [] or empty string "" or 0
- suggested_point_rewrites should contain the full rewritten bullet points (not just suggestions)
- updated_resume should be the complete rewritten resume text preserving original structure and formatting"""

GOOGLE_API_KEY = settings.google_api_key
ACCEPTABLE_ATS_SCORE = settings.acceptable_ats_score
MAX_ITERATIONS = settings.max_iterations

WORDS_TO_AVOID = [
    "Responsible", "Handled", "Assisted", "Helped", "Worked",
    "Duties", "Tasked", "Participated", "Passionate", "Motivated",
    "Creative", "Guru", "Ninja", "Expert", "Talented", "Ambitious",
    "Team-player", "Go-getter", "Hardworker", "Self-starter",
    "People-person", "Detail-oriented", "Results-oriented",
    "Dynamic", "Synergy", "Outside-the-box", "Cutting-edge",
    "Value-add", "Innovative", "Strategic", "Disruptive", "Utilized",
]

FORMATTING_REQS = [
    "Use bullet points for work experience items",
    "Keep each bullet to 1-2 lines maximum",
    "Start each bullet with a strong action verb in past tense (except current role)",
    "Include at least one quantified metric per bullet where possible",
    "Maintain consistent date formatting (Mon YYYY - Mon YYYY)",
    "Preserve section order: Summary, Skills, Work Experience, Projects, Education, Certifications",
]

DEFAULT_DEPS = ResumeOptimizer_deps(
    words_to_avoid=WORDS_TO_AVOID,
    ATS_pass_score=ACCEPTABLE_ATS_SCORE,
    formatting_reqs=FORMATTING_REQS,
)


@lru_cache
def _get_agent() -> Agent:
    """Build the optimizer agent lazily so the module imports without a key."""
    if not GOOGLE_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Add it to backend/.env (see backend/.env.example)."
        )
    provider = GoogleProvider(api_key=GOOGLE_API_KEY)
    model = GoogleModel(settings.optimizer_model, provider=provider)
    return Agent(
        model,
        output_type=ResumeOutput,
        deps_type=ResumeOptimizer_deps,
        system_prompt=system_instructions.format(
            words_to_avoid=", ".join(WORDS_TO_AVOID),
            formatting_reqs="\n".join(f"- {req}" for req in FORMATTING_REQS),
            ATS_pass_score=ACCEPTABLE_ATS_SCORE,
        ),
    )


async def AI_call(prompt: str, max_retries=5):
    agent = _get_agent()
    for attempt in range(max_retries):
        try:
            result = await agent.run(prompt, deps=DEFAULT_DEPS)
            return result.output
        except Exception as e:
            error_msg = str(e).lower()
            if any(
                term in error_msg
                for term in [
                    "429", "rate", "capacity", "resource exhausted", "quota",
                    "503", "unavailable", "high demand", "overloaded",
                ]
            ):
                wait = (2**attempt) + random.uniform(1, 3)
                logger.warning(
                    "[Retry %d/%d] Service unavailable. Waiting %.1fs...",
                    attempt + 1, max_retries, wait,
                )
                await asyncio.sleep(wait)
            else:
                raise
    raise RuntimeError(
        f"AI_call failed after {max_retries} retries due to rate limiting / service unavailability"
    )


async def inputNode(state: AgentState) -> AgentState:
    # Prefer inline text (from the API); fall back to reading file paths (CLI use).
    resume = state.get("resume_content") or ""
    jd = state.get("jd_content") or ""

    if not resume and state.get("resume_path"):
        resume = open(state["resume_path"]).read()
    if not jd and state.get("jd_path"):
        jd = open(state["jd_path"]).read()

    if not resume or not jd:
        raise ValueError(
            "Both resume and job description are required (as text or file path)."
        )

    result = await AI_call(
        f"""Extract ALL technical and professional keywords from this resume. Include:
- Programming languages and frameworks
- Tools and platforms
- Methodologies (Agile, Scrum, etc.)
- Soft skills mentioned or implied
- Domain-specific terms (e.g., "payment tokenization", "media rendering")

Return them in the resume_keywords field.
For other fields, use defaults: ATS_score=0, jd_keywords=[], matched_keywords=[], unmatched_keywords=[], suggested_point_rewrites=[], updated_resume=""

RESUME:
{resume}
"""
    )
    resume_keywords = result.resume_keywords

    return {
        "history": [AIMessage(content=f"Initial Resume Keywords: {resume_keywords}")],
        "init_resume_keywords": resume_keywords,
        "resume_content": resume,
        "jd_content": jd,
        "processing_step": "initial_resume_keywords_parsing",
        "iteration": 0,
    }


async def findingKeywords_jd(state: AgentState) -> AgentState:
    jd_content = state["jd_content"]

    result = await AI_call(
        f"""Extract ALL keywords and requirements from this job description. Include:
- Required and preferred technical skills
- Tools, frameworks, and languages mentioned
- Soft skills and qualities sought
- Years of experience requirements
- Domain-specific terms and responsibilities

Return them in the jd_keywords field.
For other fields, use defaults: ATS_score=0, resume_keywords=[], matched_keywords=[], unmatched_keywords=[], suggested_point_rewrites=[], updated_resume=""

JOB DESCRIPTION:
{jd_content}
"""
    )
    jd_keywords = result.jd_keywords

    return {
        "history": [AIMessage(content=f"JD Keywords: {jd_keywords}")],
        "jd_keywords": jd_keywords,
        "processing_step": "jd_keywords_parsing",
    }


async def findingKeywords_resume(state: AgentState) -> AgentState:
    resume_content = state["resume_content"]

    result = await AI_call(
        f"""Extract ALL technical and professional keywords from this updated resume. Include:
- Programming languages and frameworks
- Tools and platforms
- Methodologies
- Soft skills mentioned or implied
- Domain-specific terms

Return them in the resume_keywords field.
For other fields, use defaults: ATS_score=0, jd_keywords=[], matched_keywords=[], unmatched_keywords=[], suggested_point_rewrites=[], updated_resume=""

RESUME:
{resume_content}
"""
    )
    resume_keywords = result.resume_keywords

    return {
        "history": [AIMessage(content=f"Resume Keywords: {resume_keywords}")],
        "resume_keywords": resume_keywords,
        "processing_step": "resume_keywords_parsing",
    }


async def getATSScore(state, keywords, resume_content):
    result = await AI_call(
        f"""Score this resume against the job description on a scale of 0-100. Consider:
- Keyword match percentage (how many JD keywords appear in the resume)
- Relevance of work experience to the role
- Quantified achievements present
- Skills section alignment
- Overall formatting and structure

Matched keywords: {keywords.get("matched_keywords")}
Unmatched keywords (in JD but NOT in resume): {keywords.get("unmatched_keywords")}

Assign the score to ATS_score.
For other fields, use: jd_keywords=[], resume_keywords=[], matched_keywords=[], unmatched_keywords=[], suggested_point_rewrites=[], updated_resume=""

RESUME:
{resume_content}

JOB DESCRIPTION:
{state.get("jd_content")}
"""
    )
    return result.ATS_score


async def match_and_assess(state: AgentState) -> AgentState:
    resume_keywords = state["resume_keywords"]
    jd_keywords = state["jd_keywords"]

    result = await AI_call(
        f"""Compare these two keyword lists and categorize them:

RESUME KEYWORDS: {resume_keywords}
JD KEYWORDS: {jd_keywords}

Rules for matching:
- Treat semantically equivalent terms as matches (e.g., "React" = "React.js", "CI/CD" = "continuous integration", "REST" = "RESTful APIs")
- Case-insensitive matching
- Include both technical skills AND soft skills

Return:
- matched_keywords: keywords that appear in BOTH lists (or are semantically equivalent)
- unmatched_keywords: JD keywords that are MISSING from the resume (these are gaps to fill)

For other fields, use defaults: ATS_score=0, jd_keywords=[], resume_keywords=[], suggested_point_rewrites=[], updated_resume=""
"""
    )

    matched_keywords = result.matched_keywords
    unmatched_keywords = result.unmatched_keywords

    ats_score = await getATSScore(
        state=state,
        keywords={
            "matched_keywords": matched_keywords,
            "unmatched_keywords": unmatched_keywords,
        },
        resume_content=state.get("resume_content"),
    )

    return {
        "history": [
            AIMessage(
                content=f"""ATS Score: {ats_score}
                              Matched_keywords: {matched_keywords}
                              Unmatched Keywords: {unmatched_keywords}"""
            )
        ],
        "matched_keywords": matched_keywords,
        "unmatched_keywords": unmatched_keywords,
        "ats_score": ats_score,
        "processing_step": "matching_and_assessing",
    }


async def suggested_rewrites(state: AgentState) -> AgentState:
    result = await AI_call(
        f"""Rewrite the resume bullet points to incorporate the MISSING keywords from the job description.

MISSING KEYWORDS TO INCORPORATE: {state["unmatched_keywords"]}
ALREADY MATCHED KEYWORDS (keep these): {state["matched_keywords"]}

RULES:
1. Only rewrite bullets where you can NATURALLY incorporate missing keywords
2. PRESERVE all company names, job titles, dates, locations, and metrics exactly
3. Do NOT fabricate new achievements or numbers. Only update to improve the ATS scre 
4. Use strong action verbs and limit weak action verbs
5. Keep bullets concise (1-2 lines)
6. Each entry in suggested_point_rewrites should be the full rewritten bullet point.
7. DO NOT incorporate keyword to reach ats score.
8. ADD only RELEVANT EXPERIENCE which the resume only have and reword it rather than completely adding a new experience.

CURRENT RESUME:
{state["resume_content"]}

JOB DESCRIPTION:
{state["jd_content"]}

Return the rewritten bullets in suggested_point_rewrites.
For other fields: ATS_score=0, jd_keywords=[], resume_keywords=[], matched_keywords=[], unmatched_keywords=[], updated_resume=""
"""
    )
    suggested_points_rewrites = result.suggested_point_rewrites

    return {
        "history": [
            AIMessage(content=f"suggested rewrites: {suggested_points_rewrites}")
        ],
        "processing_step": "analyzing and rewriting",
    }


async def assess_and_update(state: AgentState) -> AgentState:
    result = await AI_call(
        f"""Apply the suggested rewrites to produce the final updated resume.

SUGGESTED REWRITTEN BULLET POINTS:
{state.get("history", [""])[-1]}

RULES:
1. Replace the original bullet points with the rewritten versions
2. PRESERVE the exact structure: header, summary, skills, work experience sections, education, certifications
3. PRESERVE all company names, job titles, dates, and locations EXACTLY
4. PRESERVE the skills section as-is (only bullet points in work experience should change)
5. Do NOT remove any sections
6. Return the COMPLETE updated resume in the updated_resume field

ORIGINAL RESUME:
{state.get("resume_content")}

For other fields: ATS_score=0, jd_keywords=[], resume_keywords=[], matched_keywords=[], unmatched_keywords=[], suggested_point_rewrites=[]
"""
    )
    updated_resume = result.updated_resume

    updated_ats_score = await getATSScore(
        state=state,
        keywords={
            "matched_keywords": state.get("matched_keywords"),
            "unmatched_keywords": state.get("unmatched_keywords"),
        },
        resume_content=updated_resume,
    )

    return {
        "history": [
            AIMessage(content=f"updated resume and updated_ats_score={updated_ats_score}")
        ],
        "resume_content": updated_resume,
        "ats_score": updated_ats_score,
        "iteration": state.get("iteration", 0) + 1,
    }


def output_node(state: AgentState) -> AgentState:
    return {"final_resume": state.get("resume_content")}


def resume_optimizer():
    workflow = StateGraph(AgentState)
    cp = MemorySaver()

    def check_if_resume_acceptable(state: AgentState) -> str:
        if state.get("ats_score", 0) >= ACCEPTABLE_ATS_SCORE:
            return "output"
        if state.get("iteration", 0) >= MAX_ITERATIONS:
            return "output"
        return "rewrites"

    workflow.add_node("input", inputNode)
    workflow.add_node("jdkeywords", findingKeywords_jd)
    workflow.add_node("resumekeywords", findingKeywords_resume)
    workflow.add_node("assess", match_and_assess)
    workflow.add_node("rewrites", suggested_rewrites)
    workflow.add_node("reassess", assess_and_update)
    workflow.add_node("output", output_node)

    workflow.set_entry_point("input")
    workflow.add_edge("input", "jdkeywords")
    workflow.add_edge("jdkeywords", "resumekeywords")
    workflow.add_edge("resumekeywords", "assess")
    workflow.add_conditional_edges("assess", check_if_resume_acceptable)
    workflow.add_edge("rewrites", "reassess")
    workflow.add_edge("reassess", "resumekeywords")
    workflow.add_edge("output", END)

    return workflow.compile(checkpointer=cp)


def _build_initial_state(
    resume_content="", jd_content="", resume_path=None, jd_path=None
):
    return {
        "history": [],
        "resume_path": resume_path,
        "jd_path": jd_path,
        "init_resume_keywords": [],
        "resume_content": resume_content,
        "jd_content": jd_content,
        "processing_step": "",
        "final_resume": "",
        "jd_keywords": [],
        "resume_keywords": [],
        "ats_score": 0.0,
        "matched_keywords": [],
        "unmatched_keywords": [],
        "iteration": 0,
    }


async def run_optimizer(resume_text: str, jd_text: str, thread_id: str = "api-run"):
    """Run the optimizer on resume/JD text and return a structured result dict.

    This is the entry point used by the API.
    """
    app = resume_optimizer()
    initial_state = _build_initial_state(resume_content=resume_text, jd_content=jd_text)
    config = {"configurable": {"thread_id": thread_id}}

    result = await app.ainvoke(initial_state, config)

    return {
        "ats_score": result.get("ats_score", 0),
        "iterations": result.get("iteration", 0),
        "matched_keywords": result.get("matched_keywords", []),
        "unmatched_keywords": result.get("unmatched_keywords", []),
        "jd_keywords": result.get("jd_keywords", []),
        "resume_keywords": result.get("resume_keywords", []),
        "updated_resume": result.get("final_resume", ""),
    }


async def main():
    app = resume_optimizer()
    initial_state = _build_initial_state(
        resume_path=os.path.join(DATA_DIR, "resume.txt"),
        jd_path=os.path.join(DATA_DIR, "jd.txt"),
    )
    config = {"configurable": {"thread_id": "cli-run"}}

    result = await app.ainvoke(initial_state, config)

    print("=== Final Resume ===")
    print(result.get("final_resume"))
    print(f"\n=== Final ATS Score: {result.get('ats_score')} ===")
    print(f"=== Iterations: {result.get('iteration')} ===")


if __name__ == "__main__":
    asyncio.run(main())
