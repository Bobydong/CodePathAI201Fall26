# The Unofficial Guide

Bryan Qi -- Corpus: adivce_threads


# Unit 1

## What This Does

This is a RAG question answering system for the `advice_threads` corpus that consists of 23 forum threads in which students ask a question about university life and other students reply. 
Ask it a question in that territory and it retrieves the replies that bear on it and writes an answer that cites the thread each claim came from. 
Ask it something the corpus has no opinion about and a distance cutoff stops it before it answers.


## Chunking Strategy

**Chunk size:**
A reply + the originla question prepended. The chunk size is not a fixed number. In practice it is around 132–281 characters, 202 on average. 

**Overlap:**
There is no overlap in the reply in each chunk, but the `THREAD:` question line is repeated at the top of every chunk (~50 characters), which is deliberate duplication to help with relevant context retrieval rather than overlap.

Every file in `advice_threads` is less than the starter 800 character window. It produced 26 chunks from 23 documents, which voids the benefits of chunking.

Initially, the plan was to divide each document into 3 evenly split chunks. However, this led to overlap and potential context loss if the chunk with the remaining information wasn't retrieved.  

Instead, I realized that the replies of the threads could be easily identified and separated by the rely header ex. `--- reply 3 (19 votes) ---`. This RAG chunks each document so that each chunk is a full reply. Since the replies are generally never really long, it doesn't create huge chunks. Morever, to help with finding relevant information in the retrieval section, the original question is prepended to each chunk. The relevant keywords don't have to be necessarily in the reply itself.  


<!-- What about YOUR documents made you pick these numbers? Short posts and
     long sectioned guides don't want the same chunking, and "800 seemed
     reasonable" earns nothing. Point at something you noticed when you read
     the documents in Milestone 1.

     If you changed your mind partway through, say so and say why. That's worth
     more than pretending you got it right first time.

     Milestone 3. -->

## Sample Chunks

<!-- Five chunks, pasted as text. Label each one and name the file it came from
     AND the function that produced it — the grader checks your code against
     what you claim here.

     `python app.py chunks -n 5` prints all three for you. Copy them straight
     across.

     Milestone 3. -->

**Chunk 1** — source: thread_bike_commute.txt#0 `` — produced by: chunker.py::split_documents``

```
THREAD: Is a bike worth it for a 20 minute walk commute?

--- reply 1 (14 votes) ---
Yeah. Cuts an 18 minute walk to about 6. The thing nobody mentions is storage — covered bike parking exists at three buildings and is full by 9am at all three.
```

**Chunk 2** — source: thread_first_gen.txt#1 `` — produced by: chunker.py::split_documents``

```
THREAD: Anything specific for first-generation students?

--- reply 2 (41 votes) ---
The thing I'd say: the unwritten rules are the hard part, not the coursework. Ask about the unwritten rules explicitly. People are happy to explain them and nobody volunteers them.
```

**Chunk 3** — source: thread_laptop_specs.txt#2 `` — produced by: chunker.py::split_documents`` 

```
THREAD: How much laptop do I actually need for CS courses?

--- reply 3 (12 votes) ---
I did two years on an 8GB machine and it was fine until the last project, at which point it very much wasn't. 16 is the answer.
```

**Chunk 4** — source: thread_parking.txt#1 `` — produced by: chunker.py::split_documents``

```
THREAD: Worth getting a parking permit?

--- reply 2 (21 votes) ---
Street parking on Verrill is legal and free and unmarked, which is why half the upper years do it.

```

**Chunk 5** — source: thread_sleep_schedule.txt#1 `` — produced by: chunker.py::split_documents``

```
THREAD: Everyone says fix your sleep. Does it actually matter?

--- reply 2 (37 votes) ---
The library being open until 2am is a trap. It's a resource, not a schedule.
```

## Sample Answer

<!-- One complete question and answer, pasted as text, with the source line
     visible. Milestone 4. -->

**Question:**
What do people say about the importance of textbook editions?
**Answer:**
```
(best distance 0.486, cutoff 0.7)

According to `thread_textbook_editions.txt`, you should ask your instructor directly, as most will say the previous edition is fine even if procurement reasons prevent them from putting that in the syllabus. Additionally, you can check the numbering of the current edition for free using the library reserve copy (`thread_textbook_editions.txt`).

Sources retrieved: thread_first_gen.txt, thread_first_year_regret.txt, thread_study_spots.txt, thread_textbook_editions.txt

1 model calls this session, 521 tokens (450 in, 71 out)
```

**My relevance cutoff:**
0.7

<!-- The number you set in config.py, and how you got there.

     You ran five questions your corpus covers and the five in OUT_OF_SCOPE
     that it clearly doesn't, and wrote down the best distance for each. What
     did those two groups look like? Where was the gap? Put the actual numbers
     here — the table below wants all ten rows.

     Milestone 4. -->

| Question | In corpus? | Best distance |
|---|---|---|
| How do I write a for loop in Rust | No | 0.835 |
| What is the recommended dosage of ibuprofen for a headache? | No | 0.807 |
| Who won the 1994 World Cup? | No | 0.893 |
| How do I change the oil in a diesel engine? | No | 0.896 |
| What is the capital of Mongolia? | No | 0.893 |
| How much memory should my laptop have for CS courses? | Yes | 0.334 |
| What do people say about using pass/fail for grades? | Yes | 0.486 |
| Is it worth it do get a parking permit? | Yes | 0.284 |
| What do people say about using pass/fail for grades? | Yes | 0.275 |
| How much memory should my laptop have for CS courses? | Yes | 0.159 |


## How I Used AI

<!-- Two specific moments. For each: what you asked for, what came back, and
     what you changed about it.

     "I asked Claude to write the chunking function from my notes. It ignored
     the overlap, so I added that myself" is the level of detail we're after.
     "I used AI to help me code" is not.

     Milestone 5. -->

**1.**
I came up with the original idea to chunk each document into evenly sized thirds. I asked claude to help me evaluate my idea, and it identified a few problems that came from chunking in the middle of sentences. It helped me identify that a better strategy would be to chunk so that each chunk coveres an entire reply. I modified this idea by adding that each chunk should also contain the original question as well. 

**2.**
I asked Claude to implement the improved chunking strategy. It did so, but left in the original chunking in thirds code, so I had to remove that manually. 

<!-- ── Stretch features ─────────────────────────────────────────────────────
     Doing one? Say so here BEFORE you start. A feature this README never
     claims earns nothing.
     ───────────────────────────────────────────────────────────────────────── -->

---

# Unit 2

<!-- These sections get ADDED to what's already above. Don't delete or rewrite
     unit 1 — the point is that someone can see what you said before you knew
     how it went. -->

## Run Log — Before

<!-- Your five criteria, three runs each. `python run_eval.py --label before`
     runs the questions, puts the OUT_OF_SCOPE ones through the gate, and
     writes it all into results/ for you. Targets come from criteria.md; the
     verdict column is your call.

     Criterion 3 is measured in one deterministic pass rather than three, so
     the same number goes in all three run columns. That's correct, not lazy.

     Milestone 1. -->

Source: `results/run_2026-09-23_1642.md`, three runs, caching off, top-k 5,
cutoff 0.70, response-time target 1.8s.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. At least 80% of retrieved chunks contain relevant content | 80% | no data | no data | no data | NOT MEASURED |
| 5. Each response takes ≤ 1.8 seconds | 1.8 sec | 4/5 | 5/5 | 4/5 | MISSED |


### Real output

Every excerpt below is copied verbatim from `results/run_2026-09-23_1642.md`.
Nothing here is retyped or summarised.

#### Criterion 1 — the retrieved chunks contain the answer

Produced by `store.py::search` (chunks from `chunker.py::split_documents`),
scored by `scorer.py::judge`. The `expects` value for this question was `16 GB`.

```
### How much memory should my laptop have for CS courses? — run 1

- Best distance: 0.1592 (passed the gate)
- Sources retrieved: thread_laptop_specs.txt, thread_pass_fail.txt, thread_printing.txt
- Response time: 1.68s (0.134s retrieval, 1.55s generation)

Your laptop should have 16GB of RAM. According to `thread_laptop_specs.txt`, 16GB is the one number worth paying for, and having only 8GB can cause issues on heavy final projects.
```

The answer gives the right figure and attributes it to `thread_laptop_specs.txt`,
which is in the retrieved list — so the chunk that held the answer was retrieved.
All 5 questions scored pass on all 3 runs.

#### Criterion 2 — every answer names a source

Produced by `generate.py::answer_from_chunks` under `GROUNDING_INSTRUCTION`.
Three answers from three different questions, with the citation in each:

```
### What do people say about the importance of textbook editions? — run 1

According to *thread_textbook_editions.txt*, you should ask the instructor directly about textbook editions, as most will say the previous edition is fine even if they cannot put that in the syllabus for procurement reasons. Additionally, the library reserve copy is always the current edition, allowing you to check the numbering against yours for free.
```

```
### Is it worth it do get a parking permit? — run 3

According to *thread_parking.txt*, a parking permit is worth getting if you are commuting daily (specifically the west permit), but otherwise you should not bother.
```

```
### Does fixing a sleep schedule matter? — run 2

Yes, fixing a sleep schedule matters. According to `thread_sleep_schedule.txt`, one user notes that scheduling no classes before 10am helped them rather than trying to become a morning person, and Counselling offers a practical, free four-session workshop on the topic.
```

All 15 answers in the run log name a `.txt` file this way.

#### Criterion 3 — the gate stops out-of-corpus questions

Produced by `run_eval.py::check_out_of_scope`, using `gate.py::check` against the
0.70 cutoff in `config.py`:

```
| Out-of-scope question | Best distance | Gate | Time |
|---|---|---|---|
| What is the capital of Mongolia? | 0.893 | refused | 0.122s |
| How do I change the oil in a diesel engine? | 0.896 | refused | 0.113s |
| Who won the 1994 World Cup? | 0.893 | refused | 0.109s |
| What is the recommended dosage of ibuprofen for a headache? | 0.807 | refused | 0.115s |
| How do I write a for loop in Rust? | 0.835 | refused | 0.117s |
```

Every distance is 0.807 or worse against a 0.70 cutoff, so all five were refused
before reaching the model. Each returned `gate.py::REFUSAL`:
"I don't have enough information about that."

#### Criterion 4 — at least 80% of retrieved chunks contain relevant content

**No output to paste. Nothing in the pipeline measures this.**

`run_eval.py` records which source *files* retrieval returned, not the text of
each of the 25 chunks (top-k 5 × 5 questions) or whether each one was relevant.
The closest thing the log holds is the file list, which is suggestive but is not
the measurement:

```
### What do people say about the importance of textbook editions? — run 1

- Sources retrieved: thread_first_gen.txt, thread_first_year_regret.txt, thread_study_spots.txt, thread_textbook_editions.txt
```

Three of those four files have nothing to do with textbook editions. That is a
reason to expect this criterion to be missed, but it does not establish the
chunk-level percentage, because several chunks can come from one file.

#### Criterion 5 — each response takes 1.8 seconds or less

Produced by `run_eval.py::run_once`, which times `store.py::search` plus
`generate.py::answer_from_chunks`. Scoring is excluded from the clock, and so is
time spent held back by the free tier's quota.

```
| Question | Run 1 | Run 2 | Run 3 | Median | Slowest | ≤ target |
|---|---|---|---|---|---|---|
| How much memory should my laptop have for CS courses? | 1.68s | 1.12s | 0.54s | 1.12s | 1.68s | yes |
| What do people say about using pass/fail for grades? | 2.29s | 0.93s | 1.26s | 1.26s | 2.29s | **no** |
| Is it worth it do get a parking permit? | 0.95s | 0.89s | 7.48s | 0.95s | 7.48s | **no** |
| What do people say about the importance of textbook editions? | 0.93s | 0.94s | 0.92s | 0.93s | 0.94s | yes |
| Does fixing a sleep schedule matter? | 0.82s | 0.84s | 0.82s | 0.82s | 0.84s | yes |
```

13 of 15 under the target. The two that missed, with the retrieval/generation
split that shows where the time went:

```
### What do people say about using pass/fail for grades? — run 1

- Response time: 2.29s (0.137s retrieval, 2.15s generation)
```

```
### Is it worth it do get a parking permit? — run 3

- Response time: 7.48s (0.224s retrieval, 7.26s generation)
```

Neither miss was caused by retrieval, which stayed at 0.130s median across all
15 runs. Both were the API call. The same parking question answered in 0.95s and
0.89s on its other two runs.



<!--
It's asking for **evidence**, not more prose. The table above it says `5/5` — a reader has to take that on trust. This section is where you paste the actual text your program printed, so they can check the number themselves.

The contrast the comment is drawing:

- ❌ *a description*: "The gate refused all five out-of-scope questions."
- ✅ *real output*: the actual block your code produced, pasted verbatim.

"Name the file and function that produced it" means label each excerpt with where it came from — `run_eval.py::check_out_of_scope` — so a grader can rerun it.

You've already generated all of this. It's sitting in [results/run_2026-09-23_1642.md](results/run_2026-09-23_1642.md); this section is just the relevant slices of that file, copied under each criterion. For example, criterion 3 would be:

````markdown
### Criterion 3 — the gate stops out-of-corpus questions

Produced by `run_eval.py::check_out_of_scope`, cutoff 0.70.

```
  refused  (best distance 0.893, 0.122s)  What is the capital of Mongolia?
  refused  (best distance 0.896, 0.113s)  How do I change the oil in a diesel engine?
  refused  (best distance 0.893, 0.109s)  Who won the 1994 World Cup?
  refused  (best distance 0.807, 0.115s)  What is the recommended dosage of ibuprofen?
  refused  (best distance 0.835, 0.117s)  How do I write a for loop in Rust?
  -> gate refused 5 of 5
```
````

That's the whole idea — the number in the table, and directly beneath it the output the number was read off.

What to pull for each one:

| Criterion | What counts as its real output |
|---|---|
| 1 | A question's answer plus its `Sources retrieved` line, showing the answer came from a retrieved chunk |
| 2 | Two or three full answers, with the `thread_*.txt` citations visible in the text |
| 3 | The gate table above |
| 4 | Nothing yet — this is the one with no data |
| 5 | The response-time table, or a few `Response time: 0.93s (0.130s retrieval, 0.80s generation)` lines |

Criterion 4 is the awkward one: there's no output to paste because nothing measures it. The honest move is a line saying so rather than substituting something adjacent that looks like evidence.

Want me to assemble the section from your run log? I'd pull the excerpts for 1, 2, 3 and 5, and write the placeholder for 4. Alternatively, if you'd rather criterion 4 had real data, I could add per-chunk relevance scoring to the eval — that's a larger change and it'd mean another scored run.

-->


## Verdicts

<!-- MET or MISSED for each of the five, against the target you wrote last
     unit — not a new one. Plus a sentence on how you decided. That sentence
     matters most where it was close.

     If your target said 4 of 5 and your runs came out 4, 3, 4, that's a MISS.
     The target has to hold, not show up occasionally.

     Milestone 2. -->

Judged against the targets as written in `criteria.md` in unit 1. None of them
have been revised. Evidence is `results/run_2026-09-23_1642.md`.

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 | For at least 4 of 5 questions, the retrieved chunks include one containing the answer | MET | 5 of 5 on all three runs, so the target holds on every run and not just on average. Judged indirectly, and that is the weak point: `scorer.py::judge` grades the *answer*, not the chunk. I am relying on the fact that the gate passed, `GROUNDING_INSTRUCTION` confines the model to the retrieved text, and each answer both gave the right fact and cited a file that retrieval had returned — an answer cannot be right under those conditions unless the chunk carried the answer. A stricter reading of this criterion would require reading the 5 chunks per question myself. |
| 2 | Every answer names at least one source document | MET | 15 of 15 answers name a `.txt` file. I checked this by reading all fifteen rather than by counting the `Sources retrieved` lines, because those record what retrieval returned, which is a different claim from what the answer says. The target is "every", so one bare answer would have failed it; there were none. |
| 3 | The gate refuses out-of-corpus questions in at least 4 of 5 tries | MET | 5 of 5 refused, and not narrowly: the closest out-of-scope question sat at 0.807 against a 0.70 cutoff, a margin of 0.107, while the worst in-scope question was 0.486. The two groups do not overlap, so this is a comfortable pass rather than a lucky one. Reported once rather than three times because retrieval is deterministic and the gate is a fixed comparison — re-running it cannot produce a different answer. |
| 4 | At least 80% of retrieved chunks contain relevant content | MISSED | Not measured, and an unmeasured criterion cannot be claimed as MET. Nothing in the pipeline records per-chunk relevance: with top-k 5 there are 25 chunks of context per run, and the harness logs only which files came back. This is a hole in my instrumentation rather than a demonstrated failure, and I have recorded it as MISSED instead of leaving it blank because the honest position is that I have no evidence either way. What evidence there is points the wrong way — the textbook question retrieved four files, three unrelated to textbook editions. |
| 5 | Each response takes 1.8 seconds or less | MISSED | 13 of 15. The pass/fail question took 2.29s on run 1 and the parking question 7.48s on run 3. The criterion says *each* response, so two breaches is a miss even though the median was 0.93s and 13 runs were comfortably inside. Retrieval was not the cause: it held at 0.130s median while generation ranged from 0.54s to 7.26s, so the variance is the API call. |

## Diagnoses

<!-- For each miss: which stage caused it, and how. The stage alone isn't
     enough — you need the mechanism.

     Not a diagnosis: "Question 3 didn't work."
     A diagnosis:     "Question 3 asks about laundry costs. The answer is in
                       one sentence that got split across two chunks, so
                       neither chunk on its own contains it."

     The five stages: loading → chunking → embedding → retrieval → generation.

     Look for a pattern. If three misses all ask about numbers, that's one
     problem, not three.

     Missed nothing? Say so, then say honestly whether your targets were set
     low, and which one you'd tighten and to what.

     Milestone 3. -->

Two criteria were missed, 4 and 5. Both misses land in stages the run log can
separate: criterion 4 in **retrieval**, criterion 5 in **generation**. Nothing
went wrong in loading, chunking or embedding.

### Criterion 4 — retrieval pads every question out to five chunks

**Stage: retrieval.** The mechanism is that `config.TOP_K = 5` is a fixed count
and nothing anywhere filters an individual chunk by distance. `gate.py::check`
looks at `min(r.distance for r in results)` — the *best* chunk only. Once that
one chunk is close enough, all five go into the prompt, however far away the
other four are.

Per-chunk distances, from `store.py::search` (retrieval is local and
deterministic, so this is reproducible without spending an API call):

```
How much memory should my laptop have for CS courses?
   chunk 1: 0.159  thread_laptop_specs.txt
   chunk 2: 0.230  thread_laptop_specs.txt
   chunk 3: 0.331  thread_laptop_specs.txt
   chunk 4: 0.711  thread_pass_fail.txt      <-- past the 0.70 cutoff, sent anyway
   chunk 5: 0.747  thread_printing.txt       <-- past the 0.70 cutoff, sent anyway

What do people say about the importance of textbook editions?
   chunk 1: 0.486  thread_textbook_editions.txt
   chunk 2: 0.492  thread_textbook_editions.txt
   chunk 3: 0.602  thread_first_gen.txt
   chunk 4: 0.708  thread_first_year_regret.txt   <-- past the cutoff, sent anyway
   chunk 5: 0.722  thread_study_spots.txt         <-- past the cutoff, sent anyway
```

4 of the 25 chunks sent as context are further from the question than 0.70 —
the same number the system uses to decide a question is too unrelated to answer
at all. The system is simultaneously saying "0.75 is too far to answer from" and
handing the model a 0.747 chunk as evidence.

**The pattern, and it is the interesting part:** this happens exactly where the
corpus is thin on a topic. Each question has two to four genuinely on-topic
chunks, never five, and there is a visible cliff where the on-topic material
runs out:

Taking "on topic" as "from the file the answer actually cited", and measuring
where the first chunk from a *different* file appears:

| Question | Chunks from the cited file | Its furthest | First other-file chunk | Gap | Chunks past 0.70 |
|---|---|---|---|---|---|
| Laptop memory | 3 | 0.331 | 0.711 (rank 4) | +0.380 | 2 |
| Textbook editions | 2 | 0.492 | 0.602 (rank 3) | +0.109 | 2 |
| Sleep schedule | 3 | 0.416 | 0.647 (rank 4) | +0.231 | 0 |
| Parking | 3 | 0.464 | 0.485 (rank 4) | +0.021 | 0 |
| Pass/fail | 4 | 0.473 | 0.447 (rank 4) | −0.026 | 0 |

No question has five chunks' worth of material in its own source file — the most
is four. The two questions that send chunks past the cutoff, laptop memory and
textbook editions, are the two with the fewest on-topic chunks (3 and 2) and the
largest gap before the padding starts. Where there is more material the padding
is harmless or genuinely relevant: the parking question's extra chunks come from
`thread_bike_commute.txt` at 0.485, arguably on topic for whether driving is
worth it, and the pass/fail question's other-file chunk actually *outranks* one of
its own-file chunks (0.447 against 0.473), so it is not padding at all — it is a
relevant chunk from a second thread.

Nothing is wrong with retrieval's *ranking*: chunk 1 is the right chunk every
time, which is why criterion 1 passed 5 of 5. What is wrong is that a fixed `k`
forces retrieval to keep going after it has run out of relevant material, and no
per-chunk check stops the result.

**Caveat, stated plainly:** the above is distance, not relevance, and criterion 4
asks about relevance. Distance is a proxy. Reading the retrieved files by hand
gives roughly 16 of 25 chunks on topic (64%), which is under the 80% target —
but that is my own judgement of five filenames, not a measurement, which is why
criterion 4 is recorded as MISSED for want of evidence rather than as a
demonstrated 64%.

### Criterion 5 — two misses, two different causes, both in generation

**Stage: generation, for both.** Retrieval cannot be the cause: it ran at 0.130s
median across all 15 runs and never exceeded 0.248s, against a 1.8s budget.

**Miss 1 — the parking question, 7.48s on run 3. Not a defect in this system.**
Retrieval is deterministic, so run 3 sent the model exactly the same five chunks
and the same prompt as runs 1 and 2. Those took 0.70s and 0.71s. Run 3 took
7.26s and produced a *shorter* answer than either:

```
Is it worth it do get a parking permit?
  run 1: 0.70s for 183 chars   (3.8 ms/char)
  run 2: 0.71s for 183 chars   (3.9 ms/char)
  run 3: 7.26s for 164 chars   (44.3 ms/char)
```

Same input, less output, ten times the time. Nothing in the pipeline varied
between those three calls, so the cause is latency on Google's side. This is not
something chunking, top-k or the prompt can fix.

**Miss 2 — the pass/fail question, 2.29s on run 1. Partly ours.** This is the
question that produces long answers: 520 to 707 characters, against 76 to 354 for
every other question. Its chunks cover four separate sub-topics (when to use
pass/fail, graduate-school prerequisites, the week-eight deadline, the
two-per-year limit) and `GROUNDING_INSTRUCTION` says "Be brief. Two or three
sentences is usually enough" without enforcing any limit, so the model answers
all four. More output tokens means more generation time. Across the 14 runs that
exclude the 7.26s outlier, answer length and generation time correlate at +0.55.

So the honest split on criterion 5 is that one of the two misses is the service
being slow and one is the system being verbose, and only the second is mine to
fix. With the outlier excluded the slowest response is 2.15s, still over target —
so even a perfectly behaved API would leave this criterion missed, and the 1.8s
target itself is inside the range the API varies over anyway (0.42s to 2.15s of
generation time on identical infrastructure).

## The Improvement

**What I changed:**

**Why I picked it:**

<!-- Connect it to a specific diagnosis above in one sentence. If you can't,
     you picked a fix because it sounded impressive. -->

### Run Log — After

<!-- Same format, same five criteria, three runs each.
     `python run_eval.py --label after` -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 |  |  |  |  |
| 2. Every answer names a source | 5 of 5 |  |  |  |  |
| 3. Gate stops out-of-corpus questions | 4 of 5 |  |  |  |  |
| 4. | | | | | |
| 5. | | | | | |

**Did it help?**

<!-- Say plainly whether it did, and how you know. If it made things worse,
     say that — a change that backfired, honestly reported, earns full credit
     and is more interesting than one that worked. What matters is that you can
     tell.

     Milestone 4. -->

## What's Still Broken

<!-- For each criterion still missed after your fix: what you'd do about it,
     and why you stopped where you did.

     "I ran out of time" is fine if it's true. Pretending nothing is left is
     not.

     Milestone 5. -->

## What I'd Do Differently

<!-- Knowing what you know now — which of your five criteria would you write
     differently, and why?

     Milestone 5. -->
