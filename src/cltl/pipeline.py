from transformers import pipeline, RobertaForSequenceClassification, AutoTokenizer



_LABELS={0: 'open_question_factual',
          1: 'pos_answer',
          2: 'command',
          3: 'opinion',
          4: 'statement',
          5: 'back-channeling',
          6: 'yes_no_question',
          7: 'appreciation',
          8: 'other_answers',
          9: 'thanking',
          10: 'open_question_opinion',
          11: 'hold',
          12: 'closing',
          13: 'comment',
          14: 'neg_answer',
          15: 'complaint',
          16: 'abandon',
          17: 'dev_command',
          18: 'apology',
          19: 'nonsense',
          20: 'other',
          21: 'opening',
          22: 'respond_to_apology'}


_LABEL2ID ={'open_question_factual': 0,
            'pos_answer': 1,
            'command': 2,
            'opinion': 3,
            'statement': 4,
            'back-channeling': 5,
            'yes_no_question': 6,
            'appreciation': 7,
            'other_answers': 8,
            'thanking': 9,
            'open_question_opinion': 10,
            'hold': 11, 'closing': 12,
            'comment': 13,
            'neg_answer': 14,
            'complaint': 15,
            'abandon': 16,
            'dev_command': 17,
            'apology': 18,
            'nonsense': 19,
            'other': 20,
            'opening': 21,
            'respond_to_apology': 22}

def main():
    # Path to your fine-tuned model directory
    local_model_path = "/Users/piek/Desktop/d-Leolani/leolani-models/dialogue_models/midas-da-xlmroberta"

    # Load tokenizer and model

    tokenizer = AutoTokenizer.from_pretrained(local_model_path, local_files_only=True)
    model = RobertaForSequenceClassification.from_pretrained(local_model_path, local_files_only=True, num_labels=len(_LABELS))

    # Create pipeline
    generator = pipeline("text-classification", model=model, tokenizer=tokenizer)
    label = generator("What is the weather like today?")
    print(label)

if __name__ == "__main__":
    main()