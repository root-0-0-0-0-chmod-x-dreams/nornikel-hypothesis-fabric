import asyncio
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.agents.generator import generate_hypotheses
from app.agents.actor import validate_hypothesis
from app.agents.judge import critique_hypothesis, check_pass_criteria
from app.api_mapper import hypothesis_to_api
from app.report_generator import generate_final_report
from app.sources import chunks_to_knowledge_sources
from app.config import get_config
from app.progress import ProgressEmitter

logger = logging.getLogger("hypothesis_factory")
config = get_config()


def _validate_single_hypothesis(
    *,
    index: int,
    total: int,
    hyp: dict,
    context: str,
    global_sources: list[dict],
    max_iterations: int,
    progress: ProgressEmitter,
) -> tuple[dict | None, dict | None]:
    """Run Actor→Judge cycle for one hypothesis. Returns (validated_hyp, rejection)."""
    hyp_title = str(hyp.get("title", ""))[:80]
    logger.info("step2_hypothesis", extra={"index": index + 1, "total": total, "title": hyp_title})
    progress.progress(
        "validating",
        current=index + 1,
        total=total,
        message=hyp_title,
    )

    judge_feedback = None
    for iteration in range(1, max_iterations + 1):
        logger.info(
            "actor_judge_cycle",
            extra={"iteration": iteration, "max": max_iterations, "hypothesis": index + 1},
        )

        actor_step = progress.agent_step(
            agent="actor",
            title=f"Actor · гипотеза {index + 1}/{total}",
            summary=hyp_title,
            detail="Проверка обоснования и поиск подтверждающих источников",
        )
        actor_result = validate_hypothesis(
            hyp, context, judge_feedback, prefetched_sources=global_sources
        )
        actor_verdict = actor_result.get("verdict", "pass")
        progress.agent_step(
            agent="actor",
            title=f"Actor · гипотеза {index + 1}/{total}",
            summary=str(actor_result.get("justification", ""))[:240]
            or f"Вердикт: {actor_verdict}",
            detail=str(actor_result.get("mechanism_detail", ""))[:1200],
            status="done",
            step_id=actor_step,
        )

        if actor_verdict == "reject":
            return None, {
                "hypothesis": hyp,
                "reason": actor_result.get("justification", "Actor rejected"),
            }

        judge_step = progress.agent_step(
            agent="judge",
            title=f"Judge · гипотеза {index + 1}/{total}",
            summary="Критическая оценка по 5 метрикам",
            detail="Проверка источников, рисков, механизма и KPI",
        )
        judge_result = critique_hypothesis(hyp, actor_result, context)
        judge_verdict = judge_result.get("verdict", "reject")
        score = judge_result.get("overall_score") or judge_result.get("score")
        metrics = judge_result.get("metrics") or {}
        metrics_summary = ", ".join(
            f"{k}={'✓' if v == 1 else '✗'}" for k, v in metrics.items()
        )
        progress.agent_step(
            agent="judge",
            title=f"Judge · гипотеза {index + 1}/{total}",
            summary=str(judge_result.get("critique", ""))[:240]
            or f"Вердикт: {judge_verdict}"
            + (f" · score {score}" if score is not None else ""),
            detail=metrics_summary or str(judge_result.get("blocking_issues", ""))[:800],
            status="done",
            step_id=judge_step,
        )

        if check_pass_criteria(judge_result):
            hyp = dict(hyp)
            hyp["actor_validation"] = actor_result
            hyp["judge_evaluation"] = judge_result
            hyp["knowledge_sources"] = actor_result.get("knowledge_sources") or []
            logger.info(
                "hypothesis_passed",
                extra={"title": hyp_title, "iterations": iteration},
            )
            progress.emit(
                {
                    "type": "hypothesis_passed",
                    "index": index + 1,
                    "total": total,
                    "title": hyp_title,
                }
            )
            return hyp, None

        if judge_verdict == "reject":
            return None, {
                "hypothesis": hyp,
                "reason": judge_result.get("critique", "Judge rejected"),
            }

        judge_feedback = judge_result.get("suggestions_for_actor", [])

    return None, {"hypothesis": hyp, "reason": "Max iterations exceeded"}


def process_request_sync(
    query: str,
    documents: list[str] | None = None,
    analysis_data: str = "",
    image_paths: list[str] | None = None,
    num_hypotheses: int | None = None,
    max_iterations: int | None = None,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict:
    """
    Full pipeline:
    1. Agent 1 generates hypotheses
    2. For each hypothesis: Agent 2 (Actor) + Agent 3 (Judge) cycle (parallel, max 2 workers)
    3. Generate final report
    """
    progress = ProgressEmitter(on_progress)
    max_iter = max(1, min(max_iterations or config.max_agent_iterations, 5))

    request_id = f"req_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    logger.info("pipeline_started", extra={"request_id": request_id, "query": query[:100]})
    progress.progress("analyzing", message="Запуск пайплайна генерации")

    image_descriptions: list[str] = []
    if image_paths:
        from app.mcp.vision import analyze_image

        for img_path in image_paths:
            desc = analyze_image(img_path)
            image_descriptions.append(desc)

    logger.info("step1_generator_started")
    progress.progress("retrieving", message="GraphRAG: поиск релевантных параграфов")

    hypotheses, retrieved_chunks = generate_hypotheses(
        query=query,
        documents=documents or [],
        analysis_data=analysis_data,
        image_descriptions=image_descriptions,
        num_hypotheses=num_hypotheses,
        progress=progress,
    )

    global_sources = chunks_to_knowledge_sources(retrieved_chunks)

    if not hypotheses:
        return {"success": False, "error": "No hypotheses generated", "request_id": request_id}

    logger.info("step1_done", extra={"count": len(hypotheses)})
    progress.progress(
        "generating",
        message=f"Сгенерировано {len(hypotheses)} черновых гипотез",
        total=len(hypotheses),
    )

    context = f"Запрос: {query}\n"
    if analysis_data:
        context += f"\nДанные анализа:\n{analysis_data}\n"
    if documents:
        context += "\nДокументы:\n" + "\n".join(d[:1000] for d in documents[:3])

    validated: list[dict] = []
    rejected: list[dict] = []
    total = len(hypotheses)
    workers = min(2, total)
    passed_by_index: dict[int, dict] = {}

    def run_validation(i: int, hyp: dict) -> tuple[int, dict | None, dict | None]:
        return i, *_validate_single_hypothesis(
            index=i,
            total=total,
            hyp=hyp,
            context=context,
            global_sources=global_sources,
            max_iterations=max_iter,
            progress=progress,
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_validation, i, hyp) for i, hyp in enumerate(hypotheses)]
        for future in as_completed(futures):
            i, passed_hyp, rejection = future.result()
            if passed_hyp:
                passed_by_index[i] = passed_hyp
                api_hyp = hypothesis_to_api(passed_hyp, i)
                progress.emit({"type": "hypothesis", "hypothesis": api_hyp})
            elif rejection:
                rejected.append(rejection)

    validated = [passed_by_index[i] for i in sorted(passed_by_index)]

    logger.info("step2_done", extra={"passed": len(validated), "rejected": len(rejected)})
    progress.progress(
        "report",
        message=f"Принято {len(validated)} из {total} гипотез",
        total=total,
        current=len(validated),
    )

    report = generate_final_report(
        query=query,
        hypotheses=validated,
        rejected=rejected,
        analysis_data=analysis_data,
        request_id=request_id,
    )

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
        "rejected": [
            {
                "title": r.get("hypothesis", {}).get("title", ""),
                "reason": r.get("reason", ""),
            }
            for r in rejected
        ],
        "report_markdown": report,
        "report_url": f"/api/v1/reports/{request_id}_report.md",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "global_knowledge_sources": global_sources,
    }


async def process_request(
    query: str,
    documents: list[str] | None = None,
    analysis_data: str = "",
    image_paths: list[str] | None = None,
    num_hypotheses: int | None = None,
    max_iterations: int | None = None,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict:
    return await asyncio.to_thread(
        process_request_sync,
        query,
        documents,
        analysis_data,
        image_paths,
        num_hypotheses,
        max_iterations,
        on_progress,
    )
