"""Versioned, conservative complaint phrase baseline; not a ground truth labeler."""
import re
from functools import lru_cache
TAXONOMY_VERSION = 'clothing-phrases-v2'
TOPICS = ('sizing', 'fabric_quality', 'color_appearance', 'style_design', 'value_price', 'shipping', 'customer_service', 'other')
RULES = {
 'sizing': [r'\bruns? (?:\w+ ){0,2}(?:small|large|big|short|long)\b', r'\btoo (?:\w+ ){0,2}(?:small|large|big|short|long|tight|loose|wide|narrow|low)\b', r'\b(?:odd|strange|awkward|boxy|poor|bad) (?:fit|cut|shape)\b', r'\b(?:did not|does not|doesn.t|didn.t|not|don.t|can.t|couldn.t) (?:\w+ ){0,2}fit\b', r'\b(?:oversized|unflattering|shapeless|gaping|gappy)\b', r'\b(?:dress|top|shirt|pants|sweater|skirt|it) (?:\w+ ){0,2}(?:huge|enormous)\b', r'\b(?:sizing|size) (?:is |was )?(?:off|wrong|inconsistent)\b', r'\b(?:size|sizing|fit).{0,18}(?:disappoint|not right)'],
 'fabric_quality': [r'\b(?:itchy|scratchy|flimsy|sheer|see[ -]thr(?:ough|u)|frayed|pilling|snag|snagging|shrank|shrunk|shrink|ripped|tear|torn|wrinkled|wrinkly|damaged|stains?|faded|fade|unraveling)\b', r'\b(?:poor|bad|low) quality\b', r'\b(?:cheap|thin|stiff(?:er)?) (?:\w+ ){0,2}(?:fabric|material|lace|knit)\b', r'\b(?:fabric|material|lace|knit) (?:\w+ ){0,4}(?:cheap|thin|stiff(?:er)?|heavy)\b', r'\b(?:fell|fall|falling) apart\b', r'\b(?:button|zipper|seam|thread|hem)\w* (?:\w+ ){0,4}(?:broke|break|broken|crack|pucker|bubble|rip|fray)\w*\b', r'\b(?:stretched out|saggy|sagging)\b'],
 'color_appearance': [r'\b(?:color|colour|print|pattern).{0,30}(?:wrong|different|dull|ugly|not (?:as|like)|disappoint)\w*', r'\b(?:wrong|ugly|dull) (?:color|colour|print|pattern)\b', r'\b(?:doesn.t|didn.t|does not|did not) (?:look|match).{0,20}(?:photo|picture|image|online)\b'],
 'style_design': [r'\b(?:awkward|unflattering|poorly designed|bad design|looks? cheap)\b', r'\b(?:design|style|cut).{0,25}(?:ugly|disappoint|not flattering)\w*'],
 'value_price': [r'\b(?:overpriced|too expensive|not worth|poor value|bad value)\b', r'\b(?:price|cost).{0,15}(?:too high|unreasonable|excessive)\b'],
 'shipping': [r'\b(?:late|delayed|slow|missing|lost|damaged) (?:delivery|shipping|shipment|package)\b', r'\b(?:package|order|delivery) (?:\w+ ){0,3}(?:never arrived|did not arrive|didn.t arrive|was late|arrived late)\b', r'\b(?:high|excessive|expensive|unreasonable) shipping (?:cost|fee|charge)\w*\b'],
 'customer_service': [r'\b(?:poor|bad|terrible|awful|unhelpful) customer (?:service|support)\b', r'\bcustomer (?:service|support).{0,35}(?:rude|unhelpful|never replied|never responded|ignored|refused)\b',r'\b(?:rude|unhelpful) (?:staff|service|support)\b',r'\b(?:did not|didn.t|never) (?:reply|respond|refund)\b',r'\bdo not back up their products\b',r'\btried to contact\b'],
}
COMPILED = {topic:[re.compile(pattern,re.I) for pattern in patterns] for topic,patterns in RULES.items()}

def classify_topics(text):
    labels = []
    for topic, patterns in COMPILED.items():
        for pattern in patterns:
            for match in pattern.finditer(text):
                prefix=text[max(0,match.start()-45):match.start()]
                if re.search(r'\b(?:looks?|looked) (?:like|as if).{0,25}$',prefix,re.I) and re.search(r'shr[aiu]nk',match.group(),re.I):
                    continue
                if re.search(r'\bnot (?:very |so |that )?(?:ugly|different|dull|overpriced|itchy|stiff|expensive)\b',match.group(),re.I):
                    continue
                if re.search(r'\b(?:avoid|avoiding|avoided)\s+$',prefix,re.I):
                    continue
                if re.search(r'\b(?:not|never|no|isn.t|wasn.t)\s+(?:(?:very|as|so|that)\s+)?$',prefix,re.I):
                    continue
                labels.append(topic); break
            if topic in labels: break
    return labels or ['other']


@lru_cache(maxsize=30000)
def has_explicit_complaint(text):
    return bool(text) and classify_topics(text) != ['other']
