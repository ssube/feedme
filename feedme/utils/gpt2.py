from transformers import GPT2LMHeadModel, GPT2Tokenizer


def load_model(model_path):
    model = GPT2LMHeadModel.from_pretrained(model_path)
    return model


def load_tokenizer(tokenizer_path):
    tokenizer = GPT2Tokenizer.from_pretrained(tokenizer_path)
    return tokenizer


def generate_text(model_path, prompt, max_length, top_k=50, top_p=0.95):
    model = load_model(model_path)
    tokenizer = load_tokenizer(model_path)
    ids = tokenizer.encode(f"{prompt}", return_tensors="pt")
    final_outputs = model.generate(
        ids,
        do_sample=True,
        max_new_tokens=max_length,
        pad_token_id=model.config.eos_token_id,
        top_k=top_k,
        top_p=top_p,
    )
    return tokenizer.decode(final_outputs[0], skip_special_tokens=True)
