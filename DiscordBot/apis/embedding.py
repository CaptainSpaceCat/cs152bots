import re

from numpy import dot
from numpy.linalg import norm
from sentence_transformers import SentenceTransformer
from transformers import pipeline

from apis.helper import MISINFO, NOT_MISINFO, UNCLEAR


class TextAnalysis:
    def __init__(self, threshold=0.8):
        self.contradiction_re = re.compile("(False|Inaccurate|Incorrect|Misleading|Misinformation)", re.I)
        self.threshold = threshold

        self.emb_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.entailment_model = pipeline(model="roberta-large-mnli")
        #self.sentiment_model = pipeline('sentiment-analysis')    

    def embed(self, text):
        # text can either be a single sentence or multiple sentences
        return self.emb_model.encode(text)

    def embed_sim(self, emb1, emb2):
        cos_sim = dot(emb1, emb2) / (norm(emb1) * norm(emb2))
        return cos_sim

    def is_entailment(self, text1, text2, input_type='claim'):
        combined = f"{text1.strip('.')}. {text2.strip('.')}."
        result = self.entailment_model(combined)[0]

        if input_type == 'claim':
            if result['label'] == 'ENTAILMENT' or result['label'] == 'NEUTRAL':
                return True
            return False
        if input_type == 'result':
            if self.contradiction_re.search(text2) or result['label'] == 'CONTRADICTION' or result['label'] == 'NEUTRAL':
                return False
            return True

    def get_sentiment(self, text):
        text = [text]
        result = self.sentiment_model(text)[0]
        if result['label'] == 'POSITIVE':
            label = NOT_MISINFO
        elif result['label'] == 'NEGATIVE':
            label = MISINFO
        elif result['label'] == 'NEUTRAL':
            label = UNCLEAR
        
        # If the confidence value is low, brand it as unclear
        if result['score'] < 0.6:
            label = UNCLEAR
        
        return label

#ta = TextAnalysis()
#ta.get_entailment('The Earth is flat. We have abundant evidence going back thousands of years that the Earth is roughly spherical.')
