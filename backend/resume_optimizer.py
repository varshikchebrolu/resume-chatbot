import os
from pydantic import BaseModel
from dataclasses import dataclass
from typing import TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from psycopg import Connection
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.memory import MemorySaver
import asyncio
import random


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
    initial_resume_keywords: list[str]
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
    resume_path:str
    jd_path:str


system_instructions = """You are world class resume optimizer. 
You know everything about software engineering, ATS templates, and optimizing a resume with clear and good output.
While finding out the keywords try to match keywords which are similar to each other and maintain consistency while providing those keyword results"""

DB_URI = os.getenv(
    "DATABASE_URL", "postgresql://Varshik.Chebrolu:@localhost:5432/postgres"
)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyApRvkcjfhf0wm-r4cuBRG3_VabS0TTs6k")

provider = GoogleProvider(api_key=GOOGLE_API_KEY)
model = GoogleModel("gemini-2.5-flash-lite", provider=provider)
support_agent = Agent(
    model,
    output_type=ResumeOutput,
    deps_type=ResumeOptimizer_deps,
    system_prompt=system_instructions,
)

ACCEPTABLE_ATS_SCORE = 70
MAX_ITERATIONS = 4

async def AI_call(prompt: str, max_retries=5):
    for attempt in range(max_retries):
        try:
            result = await support_agent.run(prompt)
            return result.output
        except Exception as e:
            error_msg = str(e).lower()
            if any(term in error_msg for term in ["429", "rate", "capacity", "resource exhausted", "quota"]):
                wait = (2 ** attempt) + random.uniform(0.5, 1.5)
                print(f"[Retry {attempt + 1}/{max_retries}] Rate limited. Waiting {wait:.1f}s...")
                await asyncio.sleep(wait)
            else:
                raise
    raise RuntimeError(f"AI_call failed after {max_retries} retries due to rate limiting")


async def inputNode(state: AgentState) -> AgentState:
    resume_path = state.get('resume_path')
    jd_path = state.get("jd_path")

    resume = open(resume_path).read()
    jd = open(jd_path).read()

    result = await AI_call(
        f"""Take in the resume and find all the Keywords that you can and add the keywords to resume_keywords of the output.
                              
                              RESUME: {resume}
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
        f"""Take in the job description and find all the Keywords that you can, and add the keywords to jd_keywords of the output.
                              
                              Job description: {jd_content}
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
        f"""Take in the updated resume and find all the Keywords that you can, and add the keywords to resume_keywords of the output.
                              
                              Resume: {resume_content}
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
        f"""Consider the matched Keywords between resume and JD. Also, consider the resume and JD again and give me an ATS score with respect to 100. Assign it to the value ATS_score.
                        Matched keywords: {keywords.get("matched_keywords")}
                        Unmatched keywords: {keywords.get("unmatched_keywords")}
                        
                        Resume: {resume_content}
                        Job description: {state.get("jd_content")}"""
    )
    return result.ATS_score


async def match_and_assess(state: AgentState) -> AgentState:
    resume_keywords = state["resume_keywords"]
    jd_keywords = state["jd_keywords"]

    matched_keywords = []
    unmatched_keywords = []

    for keyword in resume_keywords:
        if keyword in jd_keywords:
            matched_keywords.append(keyword)
        else:
            unmatched_keywords.append(keyword)

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
        f"""Take in all the matched and unmatched keywords from resume and job description. 
                                              Try to rewrite the points to match the current job description.
                                              matched keywords: {state["matched_keywords"]}
                                              unmatched keywords: {state["unmatched_keywords"]}
                                              
                                              resume: {state["resume_content"]}
                                              job description: {state["jd_content"]}
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
        f"""Consider the suggested rewrite points and rewrite the resume to match the job description.
                                   suggested points: {state.get("history", [""])[-1]}
                                   
                                   resume: {state.get("resume_content")}
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
            AIMessage(
                content=f"updated resume and updated_ats_score={updated_ats_score}"
            )
        ],
        "resume_content": updated_resume,
        "ats_score": updated_ats_score,
        "iteration": state.get("iteration", 0) + 1,
    }


def output_node(state: AgentState) -> AgentState:
    return {"final_resume": state.get("resume_content")}


def resume_optimizer(use_postgres=False):
    workflow = StateGraph(AgentState)

    if use_postgres:
        conn = Connection.connect(DB_URI, autocommit=True, row_factory=dict_row)
        cp = PostgresSaver(conn)
        cp.setup()
    else:
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

    app = workflow.compile(checkpointer=cp)
    return app


async def main():
    app = resume_optimizer()

    initial_state = {
        "history": [],
        "resume_path": "data/resume.txt",
        "jd_path": "data/jd.txt",
        "init_resume_keywords": [],
        "resume_content": "",
        "jd_content": "",
        "processing_step": "",
        "final_resume": "",
        "jd_keywords": [],
        "resume_keywords": [],
        "ats_score": 0.0,
        "matched_keywords": [],
        "unmatched_keywords": [],
        "iteration": 0,
    }

    config = {"configurable": {"thread_id": "test-run-1"}}

    result = await app.ainvoke(initial_state, config)

    print("=== Final Resume ===")
    print(result.get("final_resume"))
    print(f"\n=== Final ATS Score: {result.get('ats_score')} ===")
    print(f"=== Iterations: {result.get('iteration')} ===")

asyncio.run(main())
