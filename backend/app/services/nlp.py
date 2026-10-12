"""Local three-label NLP inference, pinned to an immutable Hub revision."""
MODEL_ID = 'cardiffnlp/twitter-roberta-base-sentiment-latest'
MODEL_REVISION = '3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7'
MAX_LENGTH = 256

def load_classifier(model_id, revision, cache_dir, device='auto', batch_size=16):
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, cache_dir=cache_dir, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(model_id, revision=revision, cache_dir=cache_dir, trust_remote_code=False)
    selected = ('mps' if torch.backends.mps.is_available() else 'cpu') if device == 'auto' else device
    model.to(selected).eval()
    torch.set_num_threads(4)
    labels = {int(key):value.lower() for key,value in model.config.id2label.items()}
    if set(labels.values()) != {'positive','neutral','negative'}:
        raise ValueError('Model must provide explicit positive/neutral/negative labels')
    def predict(texts):
        # Match the documented model-card normalization; input ratings are never used.
        processed=[' '.join('@user' if word.startswith('@') and len(word)>1 else 'http' if word.startswith('http') else word for word in text.split()) for text in texts]
        tokens=tokenizer(processed, padding=True, truncation=True, max_length=MAX_LENGTH, return_tensors='pt').to(selected)
        with torch.inference_mode():
            scores=model(**tokens).logits.softmax(dim=-1).cpu()
        return [(labels[int(row.argmax())],float(row.max())) for row in scores]
    return predict,selected
