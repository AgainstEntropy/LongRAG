import argparse
import json
from tqdm import tqdm
from utils.gpt_inference import GPTInference
from utils.gemini_inference import GeminiInference
from utils.claude_inference import ClaudeInference
from utils.eval_util import single_ans_em, has_correct_answer
from datasets import load_dataset
import time
import tiktoken


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test_data_name", type=str, default=None, help="Test data name")
    parser.add_argument("--test_data_split", type=str, default=None, help="Test data split")
    parser.add_argument("--output_file_path", type=str, default=None, help="Output file")
    parser.add_argument("--reader_model", type=str, default=None, help="Reader model")

    args = parser.parse_args()

    test_data = load_dataset("TIGER-Lab/LongRAG", args.test_data_name, split=args.test_data_split)
    if args.reader_model == "GPT-4o":
        llm_inference = GPTInference()
    elif args.reader_model == "Gemini":
        llm_inference = GeminiInference()

    output_file = open(args.output_file_path, 'w')
    enc = tiktoken.get_encoding("cl100k_base")
    substring_match = 0
    exact_match = 0
    tt = 0
    context_sizes = []
    start_time = time.time()

    for item in tqdm(test_data, desc="Evaluating QA"):
        question, answers = item["query"], item["answer"]
        context_titles, context = item["context_titles"], item["context"]
        context_size = len(enc.encode(context))
        context_sizes.append(context_size)
        try:
            long_ans, short_ans = llm_inference.predict_nq(context, question, context_titles)
        except:
            long_ans, short_ans = "", ""
        is_exact_match = single_ans_em(short_ans, answers)
        is_substring_match = has_correct_answer(long_ans, answers)
        # is_retrieval = (item["sp"][0] in titles) and (item["sp"][1] in titles)
        is_retrieval = has_correct_answer(context, answers)

        output = {
            "query_id": item["query_id"],
            "question": question,
            "answers": answers,
            "long_ans": long_ans,
            "short_ans": short_ans,
            "is_exact_match": is_exact_match,
            "is_substring_match": is_substring_match,
            "is_retrieval": is_retrieval,
        }
        print(output)
        tt += 1
        exact_match += is_exact_match
        substring_match += is_substring_match
        if tt % 10 == 0:
            print(f"Substring match: {substring_match / tt}")
            print(f"Exact match: {exact_match / tt}")
        json_string = json.dumps(output)
        output_file.write(json_string + "\n")

    end_time = time.time()
    print(end_time - start_time)
    print(f"Context size: {sum(context_sizes) / len(context_sizes)}")
