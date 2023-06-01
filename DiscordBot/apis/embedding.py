from numpy import dot
from numpy.linalg import norm
from sentence_transformers import SentenceTransformer
from transformers import pipeline

from apis.helper import MISINFO, NOT_MISINFO, UNCLEAR


class TextAnalysis:
    def __init__(self, threshold=0.8):
        # TODO: pre-cache the models params
        self.emb_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.sentiment_model = pipeline('sentiment-analysis')
        self.threshold = threshold

    def embed(self, text):
        # text can either be a single sentence or multiple sentences
        return self.emb_model.encode(text)

    def embed_sim(self, emb1, emb2):
        cos_sim = dot(emb1, emb2) / (norm(emb1) * norm(emb2))
        return cos_sim

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
