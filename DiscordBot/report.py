from enum import Enum, auto
import discord
import re
import json

# TODO: organize these constants so they have natural substructure

# Top level abuse reasons
MANIPULATED_CONTENT = "Manipulated or Distorted Content"
FAKE_CONTENT = "Completely Fake Content"
IMPOSTER_CONTENT = "Imposter Content"
OUT_OF_CONTEXT = "Out of Context"

# Manipulated Content Subreasons
MOD_ORIG_SOURCE = "Modified from Original Source"
MISSING_INFO = "Leaving out Important Information"
EXAGGERATION = "Misleading Exaggeration"

# Imposter Reasons
IMPOSTER = "I think this is an imposter"
FAKE_PERSON = "I think this is a fake person"

# Generic data
GENERIC_YES = "Yes"
GENERIC_NO = "No"

# System Prompts and Messages
ABUSE_PROMPT = "Select the abuse type"
MANIPULATED_PROMPT = "How has this content been manipulated?"
COUNTER_EVIDENCE_PROMPT = "Do you have counter evidence from a reputable source?"
IMPOSTER_PROMPT = "Is this impersonating a real person or organization?"
OUT_OF_CONTEXT_PROMPT = "Do you have the original context?"
REAL_ORG_PROMPT = "Do you know who the real person or organization being impersonated is?"
INTENT_TO_DECEIVE_PROMPT = "Do you think this misinformation was posted with intention to deceive?"
BLOCK_PROMPT = "Do you want to block the user?"
SUBMIT_LINK_MSG = "Please submit the URL or relevant context."
THANK_YOU_MSG = "Thank you for your report. Our content moderation team will take a look at the report and take appropriate action."


class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    FINISH_KEYWORD = "done"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.report_info = {}
        self.message = None
        self.reporting_stage = None
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]

        if message.content == self.FINISH_KEYWORD and self.state == State.REPORT_COMPLETE:
            return ["Report finished."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            self.add_to_report("User Opening Report", message.author.name)
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            self.add_to_report("URL Reported", message.content)
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
            self.add_to_report("User Being Reported", message.author.name)
            self.add_to_report("Post Reported", message.content)
            self.message = message
            #return [("", ReportTypeView())]
            #return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
            #        "This is all I know how to do right now - it's up to you to build out the rest of my reporting flow!"]
            select_options = [
                (MANIPULATED_CONTENT, "Completely false content"),
                (FAKE_CONTENT, "Distortion of information"),
                (IMPOSTER_CONTENT, "Impersonation of genuine source"),
                (OUT_OF_CONTEXT, "Accurate factual content used in a false context")
            ]
            return [(f"Found the following message: ```{message.author.name}: {message.content}```", 
                     ReportView(select_options, ABUSE_PROMPT, self._handle_report_type))]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            # Check if its awaiting a msg from 
            if self.reporting_stage == SUBMIT_LINK_MSG:
                self.reporting_stage = None
                return self._handle_report_type(SUBMIT_LINK_MSG, message.content)

            return ["Please select a reason from the above list."]

        return []


    def _handle_report_type(self, prompt, payload):
        self.add_to_report(prompt, payload)

        yes_no_select_options = [
            (GENERIC_YES, ""),
            (GENERIC_NO, "")
        ]

        # TODO: come up with a better way for distinguishing data flow besides prompt text
        #       you can probably do something with assigning a prompt # and mapping to text
        if prompt == ABUSE_PROMPT:
            if payload == MANIPULATED_CONTENT:
                select_options = [
                    (MOD_ORIG_SOURCE, ""),
                    (MISSING_INFO, ""),
                    (EXAGGERATION, "")
                ]
                return [("", ReportView(select_options, MANIPULATED_PROMPT, self._handle_report_type))]

            elif payload == FAKE_CONTENT:
                return [("", ReportView(yes_no_select_options, COUNTER_EVIDENCE_PROMPT, self._handle_report_type))]

            elif payload == IMPOSTER_CONTENT:
                select_options = [
                    (IMPOSTER, "This post is made by someone pretending to be someone they are not"),
                    (FAKE_PERSON, "This post is made by a user that doesn't actually exist (e.g. bot)")
                ]
                return [("", ReportView(select_options, IMPOSTER_PROMPT, self._handle_report_type))]
                
            elif payload == OUT_OF_CONTEXT:
                return [("", ReportView(yes_no_select_options, OUT_OF_CONTEXT_PROMPT, self._handle_report_type))]

            return []

        if prompt == MANIPULATED_PROMPT:
            return [("", ReportView(yes_no_select_options, COUNTER_EVIDENCE_PROMPT, self._handle_report_type))]

        if prompt == IMPOSTER_PROMPT:
            return [("", ReportView(yes_no_select_options, REAL_ORG_PROMPT, self._handle_report_type))]
            

        # Handle the YES/NO prompts
        if prompt in [COUNTER_EVIDENCE_PROMPT, OUT_OF_CONTEXT_PROMPT, REAL_ORG_PROMPT]:
            if payload == GENERIC_YES:
                self.reporting_stage = SUBMIT_LINK_MSG
                return [(SUBMIT_LINK_MSG)]

            elif payload == GENERIC_NO:
                return [("", ReportView(yes_no_select_options, INTENT_TO_DECEIVE_PROMPT, self._handle_report_type))]

        if prompt == SUBMIT_LINK_MSG:
            return [("", ReportView(yes_no_select_options, INTENT_TO_DECEIVE_PROMPT, self._handle_report_type))]

        if prompt == INTENT_TO_DECEIVE_PROMPT:
            return [(THANK_YOU_MSG), ("", ReportView(yes_no_select_options, BLOCK_PROMPT, self._handle_report_type))]

    
        # The final step of all reports is asking if the user should be blocked
        if prompt == BLOCK_PROMPT:
            self.state = State.REPORT_COMPLETE
            if payload == GENERIC_YES:
                return [(f"User: {self.message.author} has been blocked. Please type 'done' to finish your report.")]
            elif PAYLOAD == GENERIC_NO:
                return [f"You will continue to see content from {self.message.author}. Please type 'done' to finish your report."]
            
        return []

    def get_report(self):
        return json.dumps(self.report_info)

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE

    def add_to_report(self, key, val):
        self.report_info[key] = val


class ReportView(discord.ui.View):
    def __init__(self, select_options, prompt, callback_fn):
        super().__init__()
        self.add_item(ReportDropdown(select_options, prompt, callback_fn))


class ReportDropdown(discord.ui.Select):
    def __init__(self, select_options, prompt, callback_fn):
        self.prompt = prompt
        self.callback_fn = callback_fn
        options = [discord.SelectOption(label=option[0], description=option[1]) for option in select_options]
        super().__init__(placeholder=prompt, options=options)

    async def callback(self, interaction: discord.Interaction):
        # NOTE: if the interction is not responded to, Discord will
        #       display an error message
        responses = self.callback_fn(self.prompt, self.values[0])
        for r in responses:
            if len(r) == 2:
                msg, view = r
                await interaction.response.send_message(msg, view=view)
            else:
                if len(responses) == 1:
                    await interaction.response.send_message(r)
                else:
                    await interaction.channel.send(r)

