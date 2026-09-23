def judge(question, expects, answer, results) -> bool: 
    return expects.lower().strip() in answer.lower()
# rapidfuzz or llm as a judge