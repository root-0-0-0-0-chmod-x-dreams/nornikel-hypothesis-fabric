import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.agents.generator import generate_hypotheses
from app.agents.actor import validate_hypothesis
from app.agents.judge import critique_hypothesis, check_pass_criteria
from app.report_generator import generate_final_report
from app.config import get_config

logger = logging.getLogger("hypothesis_factory")
config = get_config()


async def process_request(
    query: str,
    documents: list[str] | None = None,
    analysis_data: str = "",
    image_paths: list[str] | None = None,
    num_hypotheses: int | None = None,
) -> dict:
    """
    Full pipeline:
    1. Agent 1 generates hypotheses
    2. For each hypothesis: Agent 2 (Actor) + Agent 3 (Judge) cycle
    3. Generate final report
    """

    request_id = f"req_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    logger.info("pipeline_started", extra={"request_id": request_id, "query": query[:100]})

    # Process images via VLM if any
    image_descriptions = []
    if image_paths:
        from app.mcp.vision import analyze_image
        for img_path in image_paths:
            desc = analyze_image(img_path)
            image_descriptions.append(desc)

    # Step 1: Generate hypotheses (Agent 1)
    logger.info("step1_generator_started")
    hypotheses = generate_hypotheses(
        query=query,
        documents=documents or [],
        analysis_data=analysis_data,
        image_descriptions=image_descriptions,
        num_hypotheses=num_hypotheses,
    )

    if not hypotheses:
        return {"success": False, "error": "No hypotheses generated", "request_id": request_id}

    logger.info("step1_done", extra={"count": len(hypotheses)})

    # Build context string
    context = f"Запрос: {query}\n"
    if analysis_data:
        context += f"\nДанные анализа:\n{analysis_data}\n"
    if documents:
        context += f"\nДокументы:\n" + "\n".join(d[:1000] for d in documents[:3])

    # Step 2: Actor-Judge cycle for each hypothesis (in parallel conceptually, but sequential here)
    validated = []
    rejected = []

    for i, hyp in enumerate(hypotheses):
        logger.info("step2_hypothesis", extra={"index": i + 1, "total": len(hypotheses), "title": hyp.get("title", "")[:80]})

        judge_feedback = None
        passed = False

        for iteration in range(1, config.max_agent_iterations + 1):
            logger.info("actor_judge_cycle", extra={"iteration": iteration, "max": config.max_agent_iterations})

            # Agent 2: Validate
            actor_result = validate_hypothesis(hyp, context, judge_feedback)

            if actor_result.get("verdict") == "reject":
                logger.info("actor_rejected", extra={"iteration": iteration})
                rejected.append({"hypothesis": hyp, "reason": actor_result.get("justification", "Actor rejected")})
                break

            # Agent 3: Critique
            judge_result = critique_hypothesis(hyp, actor_result, context)

            if check_pass_criteria(judge_result):
                # All metrics pass
                hyp["actor_validation"] = actor_result
                hyp["judge_evaluation"] = judge_result
                passed = True
                logger.info("hypothesis_passed", extra={"title": hyp.get("title", "")[:80], "iterations": iteration})
                break
            elif judge_result.get("verdict") == "reject":
                rejected.append({"hypothesis": hyp, "reason": judge_result.get("critique", "Judge rejected")})
                break
            else:
                # Judge has suggestions — feed back to Actor
                judge_feedback = judge_result.get("suggestions_for_actor", [])
                logger.info("judge_feedback", extra={"suggestions_count": len(judge_feedback)})
        else:
            # Max iterations reached
            rejected.append({"hypothesis": hyp, "reason": "Max iterations exceeded"})

        if passed:
            validated.append(hyp)

    logger.info("step2_done", extra={"passed": len(validated), "rejected": len(rejected)})

    # Step 3: Generate final report
    report = generate_final_report(
        query=query,
        hypotheses=validated,
        rejected=rejected,
        analysis_data=analysis_data,
        request_id=request_id,
    )

    # Save report
    reports_dir = Path(config.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{request_id}_report.md"
    report_path.write_text(report, encoding="utf-8")

    return {
        "success": True,
        "request_id": request_id,
        "query": query,
        "hypotheses_generated": len(hypotheses),
        "hypotheses_passed": len(validated),
        "hypotheses_rejected": len(rejected),
        "validated": validated,
        "rejected": [{"title": r.get("hypothesis", {}).get("title", ""), "reason": r.get("reason", "")} for r in rejected],
        "report_markdown": report,
        "report_url": f"/api/v1/reports/{request_id}_report.md",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
