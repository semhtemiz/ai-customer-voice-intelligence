"""Hosted model-specific request options, shared by summary and translation."""

LIGHTNING_MODEL = 'nvidia/nemotron-3.5-lightning-30b-a3b'
SUPER_MODEL = 'nvidia/nemotron-3-super-120b-a12b'


def chat_options(model):
    if model in (LIGHTNING_MODEL, SUPER_MODEL):
        # Short structured selection/translation tasks do not need reasoning tokens.
        return {'chat_template_kwargs': {'enable_thinking': False}}
    return {}
