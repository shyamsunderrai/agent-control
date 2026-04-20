"""FastAPI entrypoint for demo agents running in Kubernetes."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

AGENT_TYPE = os.getenv("AGENT_TYPE", "loan_underwriting")


def _import_agent_module():
    if AGENT_TYPE == "loan_underwriting":
        import loan_underwriting as m
    elif AGENT_TYPE == "customer_support":
        import customer_support as m
    elif AGENT_TYPE == "trade_execution":
        import trade_execution as m
    elif AGENT_TYPE == "aml_compliance":
        import aml_compliance as m
    elif AGENT_TYPE == "report_generation":
        import report_generation as m
    else:
        raise ValueError(f"Unknown AGENT_TYPE: {AGENT_TYPE}")
    return m


@asynccontextmanager
async def lifespan(app: FastAPI):
    mod = _import_agent_module()
    # Initialize agent on startup
    import agent_control
    agent_control.init(
        agent_name=mod.AGENT_NAME,
        agent_description=mod.AGENT_DESCRIPTION,
        agent_version="1.0.0",
        server_url=os.getenv("AGENT_CONTROL_URL", "http://agent-control:8000"),
        api_key=os.getenv("AGENT_CONTROL_API_KEY"),
        steps=mod.STEP_SCHEMAS,
        policy_refresh_interval_seconds=30,
    )
    app.state.module = mod
    yield
    agent_control.shutdown()


app = FastAPI(title=f"Agent Control Demo - {AGENT_TYPE}", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "agent_type": AGENT_TYPE}


@app.post("/scenarios/run")
async def run_scenarios():
    mod = app.state.module
    results = await mod.run_scenarios()
    return JSONResponse(content=[
        {
            "name": r.name,
            "description": r.description,
            "passed": r.passed,
            "action": r.action,
            "control_name": r.control_name,
            "guidance": r.guidance,
            "llm_response": r.llm_response,
            "observed_controls": r.observed_controls,
            "error": r.error,
        }
        for r in results
    ])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
