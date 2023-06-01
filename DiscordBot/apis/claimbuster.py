from collections import Counter
import requests

from apis.helper import get_config, MISINFO, NOT_MISINFO, UNCLEAR
from apis.embedding import TextAnalysis


class ClaimBuster:

    TEXT_ENDPOINT = "https://idir.uta.edu/claimbuster/api/v2/score/text/{claim}"

    KNOWLEDGE_BASE_ENDPOINT = "https://idir.uta.edu/claimbuster/api/v2/query/knowledge_bases/{claim}"

    FACT_MATCHER_ENDPOINT = "https://idir.uta.edu/claimbuster/api/v2/query/fact_matcher/{claim}"


    def __init__(self):
        config = get_config()
        self.request_headers = {"x-api-key": config['CLAIMBUSTER_API']}
        self.text_analysis = TextAnalysis()

    def get_matching_facts(self, claim, threshold=0.7):
        curr_url = self.FACT_MATCHER_ENDPOINT.format(claim=claim)
        api_response = requests.get(url=curr_url, headers=self.request_headers)
        classification_result, examples = self._parse_get_matching_facts(api_response.json(), threshold)
        return classification_result, examples

    def _parse_get_matching_facts(self, payload, threshold):
        # For each similar fact, get the true/false sentiment of the example
        payload_emb = self.text_analysis.embed(payload['claim'])

        counts = Counter(MISINFO=0, NOT_MISINFO=0, UNCLEAR=0)
        supporting_facts = []
        for fact in payload['justification']:
            # Generate embedding similarity
            curr_emb = self.text_analysis.embed(fact['claim'])
            curr_emb_sim = self.text_analysis.embed_sim(payload_emb, curr_emb)

            if curr_emb_sim > threshold:
                # Generate a positive/negative true/false classifier for the truth rating
                category = self.text_analysis.get_sentiment(fact['truth_rating'])
                counts[category] += 1

                supporting_facts.append({
                    "status": category,
                    "claim": fact['claim'],
                    "source": fact['search'],
                    "url": fact['url'],
                    "sim": curr_emb_sim,
                    "formatted_msg": f"Sim to current post: {curr_emb_sim}, Claim: {fact['claim']}, Conclusion: {category}, URL supporting conlusion: {fact['url']}"
                })

        supporting_facts.sort(key=lambda x: x['sim'], reverse=True)
    
        if len(supporting_facts) == 0:
            return UNCLEAR, [{"formatted_msg": "No similar crowd sourced reporting has verified the validity of this statement"}]

        # If one category has over 50%, then conclude that the class is correct. Otherwise say it is unclear
        classification, count = counts.most_common(1)[0]
        if count < len(supporting_facts) * 0.75:
            classification = UNCLEAR

        # Return the consensus if there is a clear majority and the list of similar claims + verifications
        return classification, supporting_facts


#cb = ClaimBuster()
#class_result, examples = cb.get_matching_facts("vaccines cause autism")
#print(class_result)
#print(examples)
