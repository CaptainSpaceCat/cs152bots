from collections import Counter
import requests

from apis.helper import get_config, MISINFO, NOT_MISINFO, UNCLEAR
from apis.embedding import TextAnalysis

class GoogleFactCheck:

    CLAIM_SEARCH_ENDPOINT = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

    def __init__(self):
        config = get_config()
        self.key = config['GOOGLE_API_KEY']

        self.text_analysis = TextAnalysis()


    def get_matching_facts(self, claim, threshold=0.75):
        payload = {
            'key': self.key,
            'query': claim
        }
        api_response = requests.get(self.CLAIM_SEARCH_ENDPOINT, params=payload)
        classification_result, examples = self._parse_get_matching_facts(claim, api_response.json(), threshold)
        return classification_result, examples

    def _parse_get_matching_facts(self, orig_claim, payload, threshold):
        orig_claim_emb = self.text_analysis.embed(orig_claim)
        counts = Counter(MISINFO=0, NOT_MISINFO=0, UNCLEAR=0)
        supporting_facts = []

        for claim in payload['claims']:

            # For now, just pick one review as a counterfactual
            if 'claimReview' not in claim or len(claim['claimReview']) == 0:
                continue

            fact_check_site = claim['claimReview'][0]['publisher']['site']
            counter_url = claim['claimReview'][0]['url']
            truth_rating = claim['claimReview'][0]['textualRating']

            claim_text = claim['text']
            curr_emb = self.text_analysis.embed(claim_text)
            curr_emb_sim = self.text_analysis.embed_sim(orig_claim_emb, curr_emb)

            # Only add as supporting evidence if it passes a given threshold
            if curr_emb_sim > threshold:
                # Generate a positive/negative true/false classifier for the truth rating
                #category = self.text_analysis.get_sentiment(fact['truth_rating'])

                # First check if the user input and the verified fact entail one another
                #  - if yes, then result entailment would mean not minsinfo
                #  - if no, then result entailment would mean misinfo
                claim_entailment = self.text_analysis.is_entailment(orig_claim, claim_text, input_type='claim')

                result_entailment = self.text_analysis.is_entailment(claim_text, truth_rating, input_type='result')

                if claim_entailment:
                    category = MISINFO
                    if result_entailment:
                        category = NOT_MISINFO
                else:
                    category = NOT_MISINFO
                    if result_entailment:
                        category = MISINFO

                counts[category] += 1

                supporting_facts.append({
                    "status": category,
                    "truth_rating": truth_rating,
                    "claim": claim_text,
                    "source": fact_check_site,
                    "url": counter_url,
                    "sim": curr_emb_sim,
                    "formatted_msg": f"Sim to current post: {curr_emb_sim}, Conclusion: {category}, URL supporting conlusion: {counter_url}, Site that Fact Checked: {fact_check_site}"
                })

        supporting_facts.sort(key=lambda x: x['sim'], reverse=True)
    
        if len(supporting_facts) == 0:
            return UNCLEAR, [{"formatted_msg": "No similar crowd sourced reporting has verified the validity of this statement"}]

        # If one category has over 66%, then conclude that the class is correct. Otherwise say it is unclear
        classification, count = counts.most_common(1)[0]
        if count < len(supporting_facts) * 0.66:
            classification = UNCLEAR

        # Return the consensus if there is a clear majority and the list of similar claims + verifications
        return classification, supporting_facts


#gfc = GoogleFactCheck()
#classification, sup_facts = gfc.get_matching_facts('the earth is flat')
#print(classification)
#print(sup_facts)
