import re

import openai

from apis.helper import get_config, MISINFO, NOT_MISINFO, UNCLEAR
from constants import MANIPULATED_CONTENT, FAKE_CONTENT, IMPOSTER_CONTENT, OUT_OF_CONTEXT

class OpenAI:
    def __init__(self):
        config = get_config()
        openai.organization = config['OPENAI_ORG']
        openai.api_key = config['OPENAI_KEY']
        self.misinfo_response_re = re.compile(f"({MISINFO}|{NOT_MISINFO}|{UNCLEAR}): (.*)")
        self.classification_re = re.compile(f"({MANIPULATED_CONTENT}|{FAKE_CONTENT}|{IMPOSTER_CONTENT}|{OUT_OF_CONTEXT})")

    def misinfo_detection(self, statement):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a misinformation detection bot. Determine if each statement is misinformation or not. Provide a URL to support this evidence if available. Do not make up facts."},
                    {"role": "user", "content": "Climate change is a hoax by the left wing media."},
                    {"role": "assistant", "content": f"{MISINFO}: scientific research by reputable sources like Stanford have shown that carbon emissions have changed modern climte conditions. Example url: https://www.factcheck.org/2022/08/unequivocal-evidence-that-humans-cause-climate-change-contrary-to-posts-of-old-video/"},
                    {"role": "user", "content": "The earth is round"},
                    {"role": "assistant", "content": f"{NOT_MISINFO}: although the Earth is not perfectly round, we know it is approximately so due to numerous scientific measurements. Example url: https://fullfact.org/online/earth-is-spherical-not-flat/"},
                    {"role": "user", "content": "My mother's name is Jasper"},
                    {"role": "assistant", "content": f"{UNCLEAR}: Personal information cannot be confirmed or refuted by a detection bot."},
                    {"role": "user", "content": f"{statement}"}
                ]
            )
            output = response['choices'][0]['message']['content']
            print(output)

            # Parse the output to get whether it is misinformation or not 
            match = self.misinfo_response_re.match(output)
            if match:
                result = match.group(1)
                rationale = match.group(2)
                return result, rationale

        except Exception as e:
            print(f"OpenAI misinfo_detection function failed: {e}")
           
        return UNCLEAR, "OpenAI response failed"

    
    def get_misinfo_type(self, statement):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"You are a misinformation classification bot. Determine what type of misinformation the following statement belongs to: {MANIPULATED_CONTENT}, {FAKE_CONTENT}, {IMPOSTER_CONTENT}, {OUT_OF_CONTEXT}. Only output the type and nothing else."},
                    {"role": "user", "content": "The moon landing was faked. NASA is lying to us, and the earth is flat."},
                    {"role": "assistant", "content": FAKE_CONTENT},
                    {"role": "user", "content": "Many people have experienced negative side effects from COVID vaccines and that's proof that they are basically poison. Medicine shouldn't make you sick!"},
                    {"role": "assistant", "content": MANIPULATED_CONTENT},
                    {"role": "user", "content": "Melting glaciers will result in the ocean absorbing more CO2, so really it isn't a problem."},
                    {"role": "assistant", "content": OUT_OF_CONTEXT},
                    {"role": "user", "content": "New Yorker Times: Donald Trump told us in an interview that 'Trans youth need to be protected.' (the thought being with the above imposter content that there is a quote misattributed to a real person, and that a fake news source was made up)."},
                    {"role": "assistant", "content": IMPOSTER_CONTENT},
                    {"role": "user", "content": f"{statement}"}
                ]
            )
            output = response['choices'][0]['message']['content']
            match = self.classification_re.match(output)
            if match:
                return output
        except Exception as e:
            print(f"OpenAI misinfo_detection function failed: {e}")
        return None
    
        
    def embedding_sim(self, sent1, sent2):
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a cosine similarity embedding model that determines how similar two pieces of text are with a 0 to 1 score with 0.5 being the cutoff threshold."},
                {"role": "user", "content": f"`{sent1}`, `{sent2}`"},
            ]
        )
        output = response['choices'][0]['message']['content']
        return output

#oa = OpenAI()
#print(oa.misinfo_detection("It will rain tomorrow"))
