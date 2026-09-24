"""
The scorer: deciding whether an answer was right.

`run_eval.py` looks for a function called `judge` in this file and uses it to
fill the Run columns in the run log. The contract it expects is:

    judge(question, expects, answer, results) -> bool

The first version of this file was a substring test — `expects.lower() in
answer.lower()`. That test measures the wrong thing. The `expects` values in
questions.py are descriptions of a correct answer ("Good for exploring
courses, but be careful with prerequisites for graduate school"), not phrases
an answer would literally contain, so a perfectly good answer worded any other
way scored as a failure. The first run log scored 1 of 5 for that reason and
not because the system was wrong 4 times.

So the judge here is a second model call: the answer, the question and the
expectation go to the same Gemini model the rest of the pipeline uses, through
the same `generate.generate()`, and it reports pass or fail with a reason.

Using the same model and the same call path is deliberate:

  • It goes through generate.py, so judging obeys the same rate limiting,
    session budget, retry and token accounting as everything else. A judge
    that bypassed the limiter would be the loop that drains your quota.
  • Judge calls are cached by default, unlike answer generation. Three eval
    runs produce three *different* answers, so the three judge prompts differ
    and are graded separately — but re-running the report over answers you've
    already graded costs nothing.

What this buys you, and what it costs:

  ✓ It reads meaning rather than matching characters, which is what "correct"
    actually means here.
  ✗ It is itself a non-deterministic system, and it can be wrong. `python
    scorer.py` at the bottom of this file grades a handful of cases whose
    right answers are known, so you can check the judge before you trust a run
    log it produced.
"""

import json
import sys

import gate
import generate

# Judge calls are cached. See the module docstring for why that is safe here
# even though `run_eval.py` turns caching off for answer generation.
CACHE_JUDGEMENTS = True


JUDGE_INSTRUCTION = """You grade answers produced by a retrieval system. You are strict about substance and indifferent to wording.

You are given a question, a short description of what a correct answer says, and the answer the system actually produced.

Mark it "pass" when the answer conveys the substance of the expected answer. Different wording, different length, extra correct detail, or a citation the expectation doesn't mention are all fine.

Mark it "fail" when the answer:
- contradicts the expectation, or
- misses the key point the expectation names, or
- refuses, hedges, or says it lacks the information, or
- answers a different question than the one asked.

The expected answer is a sketch written by a person before they saw any output. Treat it as a description of the right answer, not as required wording, and do not penalise an answer for being phrased differently. Spelling mistakes in the expectation are not meaningful.

Reply with JSON and nothing else:
{"verdict": "pass" or "fail", "reason": "one sentence", "cites_source": true or false}

"cites_source" is whether the answer names a document it drew on (a filename, or "According to ...").
"""


def build_judge_prompt(question: str, expects: str, answer: str, results) -> str:
    """Assemble the grading prompt.

    Split out from `judge` for the same reason `generate.build_prompt` is split
    out from `answer_from_chunks`: you can print what would be sent without
    sending it. `python scorer.py --show-prompt` does exactly that.

    The retrieved filenames go in so the judge can fill in `cites_source`
    against what was actually available, rather than guessing whether a name in
    the answer is a real document.
    """
    sources = sorted({r.source for r in results}) if results else []
    source_line = ", ".join(sources) if sources else "(none retrieved)"

    return (
        f"Question: {question}\n\n"
        f"Expected answer: {expects}\n\n"
        f"Documents available to the system: {source_line}\n\n"
        f"Answer produced:\n{answer}\n\n"
        f"---\n\nGrade this answer."
    )


def _parse_verdict(raw: str) -> dict | None:
    """Pull the verdict out of the model's reply.

    Models wrap JSON in ``` fences often enough that handling it here is worth
    four lines. If the JSON can't be read at all, fall back to looking for the
    words themselves before giving up, and return None if even that fails —
    the caller decides what an unreadable verdict means.
    """
    text = raw.strip()

    if text.startswith("```"):
        text = text.split("```")[1] if "```" in text[3:] else text.strip("`")
        text = text.removeprefix("json").strip()

    try:
        data = json.loads(text)
        verdict = str(data.get("verdict", "")).lower().strip()
        if verdict in ("pass", "fail"):
            return {
                "passed": verdict == "pass",
                "reason": str(data.get("reason", "")).strip(),
                "cites_source": bool(data.get("cites_source", False)),
            }
    except Exception:  # noqa: BLE001 — the keyword fallback below is the point
        pass

    lowered = text.lower()
    if '"fail"' in lowered or lowered.startswith("fail"):
        return {"passed": False, "reason": "(verdict read from unstructured reply)",
                "cites_source": False}
    if '"pass"' in lowered or lowered.startswith("pass"):
        return {"passed": True, "reason": "(verdict read from unstructured reply)",
                "cites_source": False}

    return None


def judge_detailed(question: str, expects: str, answer: str, results) -> dict:
    """Grade one answer and return the reasoning alongside the verdict.

    Returns a dict with `passed`, `reason` and `cites_source`. `judge()` below
    is the boolean wrapper `run_eval.py` calls; this is the one to use when you
    want to know *why* something failed.

    Two cases are decided here without spending a call, because the answer to
    them is not a matter of judgement:

      • The gate refused. On an in-scope question that is a failure by
        definition, and there is no answer to grade.
      • The question has no `expects` written for it. There is nothing to grade
        against, so it cannot pass.

    Errors from the model call are deliberately *not* swallowed. A judge that
    turned a network blip into "fail" would write wrong numbers into a run log
    and you would have no way to tell which ones. Better that the run stops.
    """
    answer = (answer or "").strip()
    expects = (expects or "").strip()

    if not expects:
        print(
            f"  [scorer] no `expects` written for {question!r} — cannot score it.",
            file=sys.stderr,
        )
        return {
            "passed": False,
            "reason": "no expectation written in questions.py",
            "cites_source": False,
        }

    if not answer or answer.strip() == gate.REFUSAL.strip():
        return {
            "passed": False,
            "reason": "the gate refused this question, so no answer was produced",
            "cites_source": False,
        }

    prompt = build_judge_prompt(question, expects, answer, results)
    raw = generate.generate(prompt, system=JUDGE_INSTRUCTION, cache=CACHE_JUDGEMENTS)

    verdict = _parse_verdict(raw)
    if verdict is None:
        print(
            f"  [scorer] could not read a verdict out of the judge's reply "
            f"for {question!r}. Scoring it as a failure. Reply was:\n"
            f"  {raw[:200]!r}",
            file=sys.stderr,
        )
        return {
            "passed": False,
            "reason": "judge reply could not be parsed",
            "cites_source": False,
        }

    return verdict


def judge(question: str, expects: str, answer: str, results) -> bool:
    """Was this answer right? The function `run_eval.py` calls.

    One boolean per run, which is what the run log's table holds. Use
    `judge_detailed` if you want the reason too.
    """
    return judge_detailed(question, expects, answer, results)["passed"]


# ─── Checking the judge ──────────────────────────────────────────────────────
#
# The judge is a model call, so it can be wrong, and a scorer you haven't
# checked is just a confident opinion. These are cases whose right answer is
# known: three that must pass and three that must fail. If the judge misses
# any of them, fix the judge before you trust a run log it produced.

SELF_CHECK = [
    {
        "question": "How much memory should my laptop have for CS courses?",
        "expects": "16 GB",
        "answer": "According to laptop_advice.md, most students recommend 16 GB of RAM.",
        "should_pass": True,
    },
    {
        "question": "Does fixing a sleep schedule matter?",
        "expects": "Yes",
        "answer": "From sleep_thread.md: yes, several people said fixing their sleep "
                  "schedule made the biggest difference to their grades.",
        "should_pass": True,
    },
    {
        "question": "Is it worth it to get a parking permit?",
        "expects": "No unless commuting daily",
        "answer": "Per parking.md, a permit generally isn't worth the cost unless "
                  "you're driving to campus every day.",
        "should_pass": True,
    },
    {
        "question": "How much memory should my laptop have for CS courses?",
        "expects": "16 GB",
        "answer": "According to laptop_advice.md, 4 GB of RAM is plenty for coursework.",
        "should_pass": False,
    },
    {
        "question": "Is it worth it to get a parking permit?",
        "expects": "No unless commuting daily",
        "answer": "Parking on campus is discussed in several threads and opinions vary.",
        "should_pass": False,
    },
    {
        "question": "Does fixing a sleep schedule matter?",
        "expects": "Yes",
        "answer": "I don't have enough information about that.",
        "should_pass": False,
    },
]


def self_check() -> int:
    """Grade the known cases above. Returns how many the judge got wrong."""
    print(f"Checking the judge against {len(SELF_CHECK)} known cases "
          f"(model: {generate.config.MODEL}).\n")

    wrong = 0
    for case in SELF_CHECK:
        result = judge_detailed(
            case["question"], case["expects"], case["answer"], results=[]
        )
        correct = result["passed"] == case["should_pass"]
        wrong += not correct

        got = "pass" if result["passed"] else "fail"
        want = "pass" if case["should_pass"] else "fail"
        mark = "ok  " if correct else "WRONG"
        print(f"  {mark} judged {got}, expected {want}  — {case['question']}")
        if not correct:
            print(f"        judge said: {result['reason']}")

    print()
    if wrong:
        print(f"The judge got {wrong} of {len(SELF_CHECK)} wrong. Tighten "
              f"JUDGE_INSTRUCTION before trusting it on a real run.")
    else:
        print(f"The judge got all {len(SELF_CHECK)} right.")
    print(generate.usage())
    return wrong


if __name__ == "__main__":
    if "--show-prompt" in sys.argv:
        case = SELF_CHECK[0]
        print("--- system instruction ---")
        print(JUDGE_INSTRUCTION)
        print("--- prompt ---")
        print(build_judge_prompt(
            case["question"], case["expects"], case["answer"], results=[]
        ))
    else:
        sys.exit(1 if self_check() else 0)
