# Run log — ratelimit-fix

- Produced by: `run_eval.py::main`
- Retrieval: `store.py::search`, chunks from `chunker.py::split_documents`
- Corpus: `advice_threads` (index variant `default`)
- top-k: 5 · relevance cutoff: 0.7 · response-time target: 1.8s
- Runs per question: 3, caching off
- When: 2026-09-23 16:40

This table is one row per QUESTION. The run log your README asks for is
one row per CRITERION, so aggregate these into it — criterion 1 is how many
of your questions had the answer in the retrieved chunks, and so on.

| Question | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| How much memory should my laptop have for CS courses? | pass | pass | pass |
| What do people say about using pass/fail for grades? | pass | pass | pass |
| Is it worth it do get a parking permit? | pass | pass | pass |
| What do people say about the importance of textbook editions? | pass | pass | pass |
| Does fixing a sleep schedule matter? | pass | pass | pass |

---

## Response time (criterion 5)

Produced by `run_eval.py::run_once`, ceiling 1.8s (`config.RESPONSE_TIME_TARGET`).

**14 of 15 responses came in at or under 1.8s.**

The clock starts when the question arrives and stops when the answer is
ready: retrieval, the gate, and generation. It does not include scoring —
`scorer.py` is a second model call that happens after the answer exists and
that no user waits for. The embedding model is loaded before any timing
starts, so no run carries the one-off cost of loading it.

Time spent held back by the free tier's per-minute quota is also excluded,
and reported separately below. That wait is a property of the API plan, not
of the pipeline, and it would otherwise swamp every other number here.

| Question | Run 1 | Run 2 | Run 3 | Median | Slowest | ≤ target |
|---|---|---|---|---|---|---|
| How much memory should my laptop have for CS courses? | 2.10s | 0.67s | 1.08s | 1.08s | 2.10s | **no** |
| What do people say about using pass/fail for grades? | 0.97s | 1.10s | 1.03s | 1.03s | 1.10s | yes |
| Is it worth it do get a parking permit? | 0.87s | 0.81s | 0.80s | 0.81s | 0.87s | yes |
| What do people say about the importance of textbook editions? | 1.08s | 0.77s | 0.91s | 0.91s | 1.08s | yes |
| Does fixing a sleep schedule matter? | 1.00s | 0.66s | 0.85s | 0.85s | 1.00s | yes |
⏳ 1 of 15 runs were paused by the per-minute quota, for 48s in total. That wait is excluded from the times above.


### Where the time goes

| Stage | Median | Slowest |
|---|---|---|
| Retrieval (local, no API) | 0.122s | 0.330s |
| Generation (the API call) | 0.74s | 1.99s |
| **Whole response** | **0.91s** | **2.10s** |

Splitting the two matters for diagnosis: if the total misses the target,
this says whether the cause is something you control (chunking, top-k) or
the service's latency, and those have completely different fixes.

Refusals are much faster — median 0.107s, slowest 0.115s — because a question the gate stops never
reaches the model. Those are in the out-of-scope table above and are not
counted in the numbers here, which are about answers.

---

## The relevance gate on out-of-corpus questions

Produced by `run_eval.py::check_out_of_scope`, cutoff 0.7. Refused 5 of 5.

Retrieval is deterministic and the gate is a comparison against a
fixed number, so these do not vary between runs — one pass over the
list is the whole measurement.

| Out-of-scope question | Best distance | Gate | Time |
|---|---|---|---|
| What is the capital of Mongolia? | 0.893 | refused | 0.115s |
| How do I change the oil in a diesel engine? | 0.896 | refused | 0.108s |
| Who won the 1994 World Cup? | 0.893 | refused | 0.107s |
| What is the recommended dosage of ibuprofen for a headache? | 0.807 | refused | 0.105s |
| How do I write a for loop in Rust? | 0.835 | refused | 0.107s |

---

## Real output

This is what the system actually produced. Paste the relevant parts
into your README underneath the table — the rubric asks for real
output as text, not a description of it.

### How much memory should my laptop have for CS courses? — run 1

- Best distance: 0.1592 (passed the gate)
- Sources retrieved: thread_laptop_specs.txt, thread_pass_fail.txt, thread_printing.txt
- Response time: 2.10s (0.113s retrieval, 1.99s generation)

```
According to `thread_laptop_specs.txt`, your laptop should have 16GB of RAM. The documents note that 16GB is the one number worth paying for, and that while an 8GB machine can work initially, it will struggle by the time you reach the final projects.
```

### How much memory should my laptop have for CS courses? — run 2

- Best distance: 0.1592 (passed the gate)
- Sources retrieved: thread_laptop_specs.txt, thread_pass_fail.txt, thread_printing.txt
- Response time: 0.67s (0.104s retrieval, 0.57s generation)

```
According to `thread_laptop_specs.txt`, your laptop should have 16GB of RAM.
```

### How much memory should my laptop have for CS courses? — run 3

- Best distance: 0.1592 (passed the gate)
- Sources retrieved: thread_laptop_specs.txt, thread_pass_fail.txt, thread_printing.txt
- Response time: 1.08s (0.121s retrieval, 0.96s generation)

```
According to `thread_laptop_specs.txt`, your laptop should have 16GB of RAM. The documents state that 16GB is the one number worth paying for, and that 8GB machines can struggle by the final projects.
```

### What do people say about using pass/fail for grades? — run 1

- Best distance: 0.2750 (passed the gate)
- Sources retrieved: thread_first_year_regret.txt, thread_pass_fail.txt
- Response time: 0.97s (0.228s retrieval, 0.74s generation)

```
According to `thread_first_year_regret.txt` and `thread_pass_fail.txt`, you can declare a course pass/fail late—up to week eight—so you can take the midterm first before deciding. Additionally, `thread_pass_fail.txt` notes that some graduate programs may want a letter grade for prerequisites and a "P" grade will not satisfy it.
```

### What do people say about using pass/fail for grades? — run 2

- Best distance: 0.2750 (passed the gate)
- Sources retrieved: thread_first_year_regret.txt, thread_pass_fail.txt
- Response time: 1.10s (0.269s retrieval, 0.83s generation)

```
According to *thread_first_year_regret.txt* and *thread_pass_fail.txt*, you can declare a course pass/fail as late as week eight, allowing you to take the midterm first and decide afterward. Additionally, *thread_pass_fail.txt* notes that graduate programs may require a letter grade for prerequisites instead of a "P", and the option is best used for curious courses outside your major.
```

### What do people say about using pass/fail for grades? — run 3

- Best distance: 0.2750 (passed the gate)
- Sources retrieved: thread_first_year_regret.txt, thread_pass_fail.txt
- Response time: 1.03s (0.122s retrieval, 0.91s generation)

```
According to `thread_pass_fail.txt`, you should use the pass/fail option for a course outside your major that you are taking out of curiosity. However, you should be careful if you are applying to graduate programs, as some require a letter grade for prerequisites and a "P" will not satisfy it (`thread_pass_fail.txt`). Additionally, you can wait to declare pass/fail as late as week eight, allowing you to take the midterm first and decide based on that grade (`thread_pass_fail.txt`, `thread_first_year_regret.txt`).
```

### Is it worth it do get a parking permit? — run 1

- Best distance: 0.2845 (passed the gate)
- Sources retrieved: thread_bike_commute.txt, thread_parking.txt
- Response time: 0.87s (0.172s retrieval, 0.70s generation)

```
According to *thread_parking.txt*, a parking permit is worth getting if you are commuting daily (specifically the west permit), but otherwise you should not bother.
```

### Is it worth it do get a parking permit? — run 2

- Best distance: 0.2845 (passed the gate)
- Sources retrieved: thread_bike_commute.txt, thread_parking.txt
- Response time: 0.81s (0.324s retrieval, 0.48s generation)

```
According to `thread_parking.txt`, the west parking permit is worth getting if you are commuting daily. Otherwise, the thread advises not to bother.
```

### Is it worth it do get a parking permit? — run 3

- Best distance: 0.2845 (passed the gate)
- Sources retrieved: thread_bike_commute.txt, thread_parking.txt
- Response time: 0.80s (0.179s retrieval, 0.62s generation)

```
According to *thread_parking.txt*, a parking permit is worth getting if you are commuting daily (specifically the west permit), but otherwise you should not bother.
```

### What do people say about the importance of textbook editions? — run 1

- Best distance: 0.4864 (passed the gate)
- Sources retrieved: thread_first_gen.txt, thread_first_year_regret.txt, thread_study_spots.txt, thread_textbook_editions.txt
- Response time: 1.08s (0.330s retrieval, 0.75s generation)

```
According to `thread_textbook_editions.txt`, you should ask your instructor directly, as most will say the previous edition is fine even if they cannot put that in the syllabus for procurement reasons. Additionally, you can check the numbering of a previous edition against the current edition for free using the library reserve copy.
```

### What do people say about the importance of textbook editions? — run 2

- Best distance: 0.4864 (passed the gate)
- Sources retrieved: thread_first_gen.txt, thread_first_year_regret.txt, thread_study_spots.txt, thread_textbook_editions.txt
- Response time: 0.77s (0.110s retrieval, 0.66s generation)

```
According to *thread_textbook_editions.txt*, people suggest asking the instructor directly because most will say the previous edition is fine, even though they cannot put that in the syllabus for procurement reasons. Additionally, you can check the numbering of the current edition for free using the library reserve copy (*thread_textbook_editions.txt*).
```

### What do people say about the importance of textbook editions? — run 3

- Best distance: 0.4864 (passed the gate)
- Sources retrieved: thread_first_gen.txt, thread_first_year_regret.txt, thread_study_spots.txt, thread_textbook_editions.txt
- Response time: 0.91s (0.140s retrieval, 0.77s generation)

```
According to *thread_textbook_editions.txt*, you can check the numbering of the current edition for free using the library reserve copy. Additionally, instructors should be asked directly about the edition, as most will say the previous edition is fine even if procurement reasons prevent them from putting that in the syllabus.
```

### Does fixing a sleep schedule matter? — run 1

- Best distance: 0.3336 (passed the gate)
- Sources retrieved: thread_commuting.txt, thread_office_hours_etiquette.txt, thread_sleep_schedule.txt
- Response time: 1.00s (0.118s retrieval, 0.88s generation)

```
From `thread_sleep_schedule.txt`, the answer is yes. One user notes that fixing sleep matters, and the specific adjustment that helped them was scheduling no classes before 10am rather than trying to become a morning person.
```

### Does fixing a sleep schedule matter? — run 2

- Best distance: 0.3336 (passed the gate)
- Sources retrieved: thread_commuting.txt, thread_office_hours_etiquette.txt, thread_sleep_schedule.txt
- Response time: 0.66s (0.112s retrieval, 0.55s generation)

```
According to `thread_sleep_schedule.txt`, fixing your sleep does matter, and one helpful strategy is scheduling no classes before 10am rather than trying to become a morning person. Additionally, counselling offers a practical, free, four-session workshop on the topic.
```

### Does fixing a sleep schedule matter? — run 3

- Best distance: 0.3336 (passed the gate)
- Sources retrieved: thread_commuting.txt, thread_office_hours_etiquette.txt, thread_sleep_schedule.txt
- Response time: 0.85s (0.122s retrieval, 0.73s generation)

```
According to thread_sleep_schedule.txt, fixing your sleep does matter, and one user found it helpful to schedule no classes before 10am rather than trying to become a morning person.
```
