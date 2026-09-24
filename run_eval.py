#!/usr/bin/env python3
"""
Run your test questions repeatedly and write the results down.

    python run_eval.py                 three runs, the default
    python run_eval.py --runs 5        more runs
    python run_eval.py --label after   name this run, e.g. before/after a fix

This does the mechanical half of unit 2 for you: it asks each of your questions
the same way three separate times, with caching turned off so you get three
real answers, and writes everything into results/ as a table with one row per
question.

It also puts every question in `OUT_OF_SCOPE` through retrieval and the gate
and records what happened, so criterion 3 — the one about out-of-corpus
questions — has evidence in the same file as the other four. That part costs
nothing: a question the gate refuses never reaches the model.

It also times every response — retrieval, gate and generation — and writes a
table of those times against the target in `config.RESPONSE_TIME_TARGET`, so
criterion 5 has evidence in the same file as the rest. The clock stops before
the answer is scored: the judge is a second model call that no user waits for.

That table is the raw material for your run log, not the run log itself. The
submission template wants one row per *criterion* — aggregating your questions
up into your criteria is your work, not the script's.

⚠️ What it does NOT do is decide whether an answer was right.

That judgment is yours, and you'll build it in class in unit 2 as `scorer.py`.
Until that file exists, the Run columns carry the raw answers and you read them
yourself. Once it exists — a file called `scorer.py`, with a function
`judge(question, expects, answer, results) -> bool` — this script finds it
automatically and the Run columns carry verdicts instead.

Deciding what counts as correct is the actual lesson. It would be easy to hand
you a scorer; you'd learn nothing from it.
"""

import argparse
import datetime as dt
import statistics
import sys
import time
from pathlib import Path

import config
import questions as qs


def load_scorer():
    """Use scorer.py if the student has built it. Otherwise run unscored."""
    try:
        import scorer  # noqa: PLC0415
    except ImportError:
        return None
    judge = getattr(scorer, "judge", None)
    return judge if callable(judge) else None


def warm_up(corpus, variant):
    """Load the embedding model before anything is timed.

    store.py loads the embedder lazily, on the first search. That load is tens
    of megabytes and takes seconds, and it happens once per process — so
    without this, run 1 of question 1 would be timed with the model download
    inside it and every later run without. That single number would then be the
    worst in the table, for a reason that has nothing to do with how fast the
    system answers.

    A user of a running system never pays that cost, so it does not belong in a
    measurement of what a user waits for.
    """
    from store import search

    print("Loading the embedding model before timing anything...")
    started = time.perf_counter()
    search("warm up", top_k=1, corpus=corpus, variant=variant)
    print(f"  ready in {time.perf_counter() - started:.2f}s (not counted)\n")


def run_once(question: str, top_k, threshold, corpus, variant):
    """One question, one run. Returns the answer, retrieval, gate and timings.

    The clock covers retrieval + gate + generation: everything between the
    question arriving and the answer being ready, which is what criterion 5 is
    about. It deliberately stops before `scorer.py` grades the answer — the
    judge is a second model call that roughly doubles the wall time of an eval,
    and no user ever waits for it.
    """
    from store import search
    import gate
    import generate
    from generate import answer_from_chunks

    started = time.perf_counter()
    results = search(question, top_k=top_k, corpus=corpus, variant=variant)
    retrieval_seconds = time.perf_counter() - started

    decision = gate.check(results, threshold=threshold)

    if not decision.passed:
        total = time.perf_counter() - started
        timing = {
            "retrieval": retrieval_seconds,
            "generation": 0.0,     # refused, so the model was never called
            "total": total,
            "waited": 0.0,
        }
        return gate.REFUSAL, results, decision, timing

    # Clear any wait the judge's call left behind, so what we subtract below is
    # this generation's wait and nothing else.
    generate.take_waited_seconds()

    # cache=False on purpose. Three runs have to be three real answers.
    generation_started = time.perf_counter()
    answer = answer_from_chunks(question, results, cache=False)
    elapsed = time.perf_counter() - generation_started

    # Time spent held back by the free tier's quota is not time the system took
    # to answer. Counting it would make criterion 5 a measurement of Google's
    # rate limit rather than of this pipeline. It is reported separately instead
    # of thrown away, because a run that waited a lot is worth knowing about.
    waited = generate.take_waited_seconds()
    generation_seconds = max(elapsed - waited, 0.0)

    timing = {
        "retrieval": retrieval_seconds,
        "generation": generation_seconds,
        "total": retrieval_seconds + generation_seconds,
        "waited": waited,
    }
    return answer, results, decision, timing


def main():
    parser = argparse.ArgumentParser(description="Run the test questions and log the results.")
    parser.add_argument("--runs", type=int, default=3, help="runs per question (default 3)")
    parser.add_argument("--label", default="", help="a name for this run, e.g. 'before'")
    parser.add_argument("--corpus", default=None)
    parser.add_argument("--variant", default="default")
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument(
        "--target-seconds",
        type=float,
        default=None,
        help=f"response-time ceiling for criterion 5 "
             f"(default {config.RESPONSE_TIME_TARGET} from config.py)",
    )
    args = parser.parse_args()

    corpus = args.corpus or config.CORPUS
    top_k = args.top_k or config.TOP_K
    threshold = config.THRESHOLD if args.threshold is None else args.threshold
    target_seconds = (
        config.RESPONSE_TIME_TARGET
        if args.target_seconds is None
        else args.target_seconds
    )

    items = qs.answered()
    if not items:
        print(
            "questions.py has no questions in it yet.\n"
            "Milestone 2 asks you to write five. Fill them in and run this again.",
            file=sys.stderr,
        )
        sys.exit(1)

    judge = load_scorer()
    if judge is None:
        print("No scorer.py found — running unscored. Verdict column will be blank.")
        print("You'll build scorer.py in class in unit 2.\n")

    if args.runs < 3:
        print(f"⚠️  {args.runs} run(s). The submission asks for three.\n")

    warm_up(corpus, args.variant)

    transcript = []
    rows = []

    for item in items:
        question = item["question"]
        expects = item.get("expects", "")
        print(f"\n{question}")

        run_results = []
        run_timings = []
        for run in range(1, args.runs + 1):
            answer, results, decision, timing = run_once(
                question, top_k, threshold, corpus, args.variant
            )
            run_timings.append(timing)

            # The judge runs after the clock has stopped. See run_once.
            passed = judge(question, expects, answer, results) if judge else None
            run_results.append(passed)

            mark = {True: "pass", False: "fail", None: "—"}[passed]
            within = "✓" if timing["total"] <= target_seconds else "✗"
            waited = (
                f", waited {timing['waited']:.0f}s for quota"
                if timing["waited"] > 0.5 else ""
            )
            print(
                f"  run {run}: {mark}  "
                f"(best distance {decision.best_distance:.3f}, "
                f"{timing['total']:.2f}s {within}{waited})"
            )

            transcript.append(
                {
                    "question": question,
                    "run": run,
                    "answer": answer,
                    "sources": sorted({r.source for r in results}),
                    "best_distance": decision.best_distance,
                    "gate_passed": decision.passed,
                    "timing": timing,
                }
            )

        rows.append(
            {
                "question": question,
                "expects": expects,
                "runs": run_results,
                "timings": run_timings,
            }
        )

    gate_rows = check_out_of_scope(top_k, threshold, corpus, args.variant)

    write_report(
        rows, transcript, gate_rows, args, corpus, top_k, threshold,
        scored=judge is not None, target_seconds=target_seconds,
    )


def check_out_of_scope(top_k, threshold, corpus, variant):
    """Put every OUT_OF_SCOPE question through retrieval and the gate.

    Criterion 3 in criteria.md is about questions the corpus doesn't cover, and
    it needs evidence in the run log like the other four. This costs nothing:
    a question the gate refuses never reaches the model, so there is no API
    call and no reason to run it three times — retrieval is deterministic and
    the gate is a comparison against a fixed number.
    """
    from store import search
    import gate

    questions = getattr(qs, "OUT_OF_SCOPE", [])
    if not questions:
        return []

    print("\nOut-of-scope questions (the gate should refuse these):")
    rows = []
    for question in questions:
        started = time.perf_counter()
        results = search(question, top_k=top_k, corpus=corpus, variant=variant)
        decision = gate.check(results, threshold=threshold)
        elapsed = time.perf_counter() - started

        refused = not decision.passed
        print(f"  {'refused' if refused else 'LET THROUGH'}  "
              f"(best distance {decision.best_distance:.3f}, {elapsed:.2f}s)  {question}")
        rows.append(
            {
                "question": question,
                "refused": refused,
                "best_distance": decision.best_distance,
                "seconds": elapsed,
            }
        )

    kept = sum(r["refused"] for r in rows)
    print(f"  -> gate refused {kept} of {len(rows)}")
    return rows


def timing_section(rows, gate_rows, target_seconds):
    """The evidence for criterion 5, as a table you can read a number off.

    Reports the slowest run per question as well as the median, because the
    criterion says *each* response, not the average one. An average hides the
    single four-second outlier that a criterion worded this way is exactly
    about, so the verdict column is decided by the maximum.
    """
    answered = [t for row in rows for t in row["timings"]]
    if not answered:
        return []

    totals = [t["total"] for t in answered]
    retrievals = [t["retrieval"] for t in answered]
    generations = [t["generation"] for t in answered]

    within = sum(t <= target_seconds for t in totals)

    lines = [
        "",
        "---",
        "",
        "## Response time (criterion 5)",
        "",
        f"Produced by `run_eval.py::run_once`, ceiling {target_seconds}s "
        f"(`config.RESPONSE_TIME_TARGET`).",
        "",
        f"**{within} of {len(totals)} responses came in at or under "
        f"{target_seconds}s.**",
        "",
        "The clock starts when the question arrives and stops when the answer is",
        "ready: retrieval, the gate, and generation. It does not include scoring —",
        "`scorer.py` is a second model call that happens after the answer exists and",
        "that no user waits for. The embedding model is loaded before any timing",
        "starts, so no run carries the one-off cost of loading it.",
        "",
        "Time spent held back by the free tier's per-minute quota is also excluded,",
        "and reported separately below. That wait is a property of the API plan, not",
        "of the pipeline, and it would otherwise swamp every other number here.",
        "",
        "| Question | " + " | ".join(
            f"Run {i}" for i in range(1, len(rows[0]["timings"]) + 1)
        ) + " | Median | Slowest | ≤ target |",
        "|---|" + "|".join(["---"] * (len(rows[0]["timings"]) + 3)) + "|",
    ]

    for row in rows:
        per_run = [t["total"] for t in row["timings"]]
        slowest = max(per_run)
        cells = " | ".join(f"{t:.2f}s" for t in per_run)
        verdict = "yes" if slowest <= target_seconds else "**no**"
        question = row["question"].replace("|", "\\|")
        lines.append(
            f"| {question} | {cells} | {statistics.median(per_run):.2f}s | "
            f"{slowest:.2f}s | {verdict} |"
        )

    waits = [t.get("waited", 0.0) for t in answered]
    if sum(waits) > 0.5:
        paused = sum(w > 0.5 for w in waits)
        lines += [
            f"⏳ {paused} of {len(waits)} runs were paused by the per-minute quota, "
            f"for {sum(waits):.0f}s in total. That wait is excluded from the times "
            f"above.",
            "",
        ]

    lines += [
        "",
        "### Where the time goes",
        "",
        "| Stage | Median | Slowest |",
        "|---|---|---|",
        f"| Retrieval (local, no API) | {statistics.median(retrievals):.3f}s "
        f"| {max(retrievals):.3f}s |",
        f"| Generation (the API call) | {statistics.median(generations):.2f}s "
        f"| {max(generations):.2f}s |",
        f"| **Whole response** | **{statistics.median(totals):.2f}s** "
        f"| **{max(totals):.2f}s** |",
        "",
        "Splitting the two matters for diagnosis: if the total misses the target,",
        "this says whether the cause is something you control (chunking, top-k) or",
        "the service's latency, and those have completely different fixes.",
    ]

    if gate_rows and any("seconds" in r for r in gate_rows):
        refusal_times = [r["seconds"] for r in gate_rows if "seconds" in r]
        lines += [
            "",
            f"Refusals are much faster — median "
            f"{statistics.median(refusal_times):.3f}s, slowest "
            f"{max(refusal_times):.3f}s — because a question the gate stops never",
            "reaches the model. Those are in the out-of-scope table above and are not",
            "counted in the numbers here, which are about answers.",
        ]

    return lines


def write_report(rows, transcript, gate_rows, args, corpus, top_k, threshold, scored,
                 target_seconds):
    config.RESULTS_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    label = f"_{args.label}" if args.label else ""
    path = config.RESULTS_DIR / f"run_{stamp}{label}.md"

    n = len(rows[0]["runs"]) if rows else 0
    run_headers = " | ".join(f"Run {i}" for i in range(1, n + 1))
    run_divider = "|".join(["---"] * n)

    lines = [
        f"# Run log{f' — {args.label}' if args.label else ''}",
        "",
        f"- Produced by: `run_eval.py::main`",
        f"- Retrieval: `store.py::search`, chunks from `chunker.py::split_documents`",
        f"- Corpus: `{corpus}` (index variant `{args.variant}`)",
        f"- top-k: {top_k} · relevance cutoff: {threshold} · "
        f"response-time target: {target_seconds}s",
        f"- Runs per question: {n}, caching off",
        f"- When: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "This table is one row per QUESTION. The run log your README asks for is",
        "one row per CRITERION, so aggregate these into it — criterion 1 is how many",
        "of your questions had the answer in the retrieved chunks, and so on.",
        "",
        f"| Question | {run_headers} |",
        f"|---|{run_divider}|",
    ]

    for row in rows:
        cells = []
        for passed in row["runs"]:
            cells.append({True: "pass", False: "fail", None: " "}[passed])
        question = row["question"].replace("|", "\\|")
        lines.append(f"| {question} | {' | '.join(cells)} |")

    if not scored:
        lines += [
            "",
            "> The Run columns are blank because `scorer.py` doesn't exist yet.",
            "> Judge each question yourself by reading the output below, or build",
            "> the scorer first and re-run.",
        ]

    lines += timing_section(rows, gate_rows, target_seconds)

    if gate_rows:
        refused = sum(r["refused"] for r in gate_rows)
        lines += [
            "",
            "---",
            "",
            "## The relevance gate on out-of-corpus questions",
            "",
            f"Produced by `run_eval.py::check_out_of_scope`, cutoff {threshold}. "
            f"Refused {refused} of {len(gate_rows)}.",
            "",
            "Retrieval is deterministic and the gate is a comparison against a",
            "fixed number, so these do not vary between runs — one pass over the",
            "list is the whole measurement.",
            "",
            "| Out-of-scope question | Best distance | Gate | Time |",
            "|---|---|---|---|",
        ]
        for row in gate_rows:
            question = row["question"].replace("|", "\\|")
            verdict = "refused" if row["refused"] else "**let through**"
            seconds = f"{row['seconds']:.3f}s" if "seconds" in row else "—"
            lines.append(
                f"| {question} | {row['best_distance']:.3f} | {verdict} | {seconds} |"
            )

    lines += ["", "---", "", "## Real output", "",
              "This is what the system actually produced. Paste the relevant parts",
              "into your README underneath the table — the rubric asks for real",
              "output as text, not a description of it.", ""]

    for entry in transcript:
        lines += [
            f"### {entry['question']} — run {entry['run']}",
            "",
            f"- Best distance: {entry['best_distance']:.4f} "
            f"({'passed' if entry['gate_passed'] else 'refused by'} the gate)",
            f"- Sources retrieved: {', '.join(entry['sources']) or 'none'}",
            f"- Response time: {entry['timing']['total']:.2f}s "
            f"({entry['timing']['retrieval']:.3f}s retrieval, "
            f"{entry['timing']['generation']:.2f}s generation)",
            "",
            "```",
            entry["answer"],
            "```",
            "",
        ]

    path.write_text("\n".join(lines), encoding="utf-8")

    import generate as gen

    print(f"\nWrote {path.relative_to(config.ROOT)}")
    print(gen.usage())
    print("\nCommit this file. It's the evidence the run actually happened.")


if __name__ == "__main__":
    main()
