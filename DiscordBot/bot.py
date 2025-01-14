# bot.py
import json
import logging
import os
import pdb
import re
import requests

import discord
from discord.ext import commands

from apis.helper import MISINFO, NOT_MISINFO, UNCLEAR
from apis.claimbuster import ClaimBuster
from apis.googlefactcheck import GoogleFactCheck
from apis.openaichat import OpenAI
from report import Report
from mod import ModReview


# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.mod_review = {} # Map from user IDs to mod reviews
        self.submitted_reports = [] # List of submitted reports

        # Initialize the various apis
        self.openai = OpenAI()
        self.claimbuster = ClaimBuster()
        self.googlefactcheck = GoogleFactCheck()

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
        

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        # Ignore messages from the bot 
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)


    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            # TODO: add a more sophisticated method for evaluating this
            #       and updating the report
            if len(r) == 2:
                msg, view = r
                await message.channel.send(msg, view=view)
            else:
                await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_end():
            report = self.reports.pop(author_id)

            # If the report is complete, save it to list of reports for mod to review
            if report.report_complete():
                # TODO: implementsomething more sophisticated that scales better for sorting
                self.submitted_reports.append(report)
                self.submitted_reports.sort(reverse=True)

                # Notify the mod channel that a new report has been submitted
                mod_channel = self.mod_channels[report.message.guild.id]
                await mod_channel.send(f"Received new report.")
                

            # Also send the message to the mod channel with all details
            #mod_channel = self.mod_channels[report.message.guild.id]
            #await mod_channel.send(f"Generated report: {report.get_report()}")

    async def handle_channel_message(self, message):

        if message.channel.name == f'group-{self.group_num}':
            # Forward the message to the mod channel
            mod_channel = self.mod_channels[message.guild.id]
            #await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
            data_payload = self.eval_text(message.content)

            base_msg = f'New post by user `{message.author.name}`\n"{message.content}"\n\n'
            aux_msgs = self.code_format(data_payload)

            await mod_channel.send(base_msg)
            for msg in aux_msgs:
                if msg == "-DELETE-":
                    await message.delete()
                    continue
                await mod_channel.send(msg)

        elif message.channel.name == f'group-{self.group_num}-mod':
            # TODO: implement locks to allow multiple mods to review at the same time
            mod_channel = self.mod_channels[message.guild.id]

            if message.content == ModReview.LIST_REPORTS:
                reports_msg = ModReview.list_reports(self.submitted_reports)
                await mod_channel.send(reports_msg)

            elif message.content == ModReview.REVIEW_URGENT_REPORT:
                # For now, each moderator can only review one report at a time and
                # there is no customer interaction
                
                author_id = message.author.id
                if author_id not in self.mod_review:
                    # Take the most urgent report and review it
                    most_urgent = self.submitted_reports.pop(0)
                    self.mod_review[author_id] = ModReview(self, most_urgent)
                    # Start the moderator flow using drop down boxes

                    responses = await self.mod_review[author_id].handle_message(message)
                    for r in responses:
                        if len(r) == 2:
                            msg, view = r
                            await message.channel.send(msg, view=view)
                        else:
                            await message.channel.send(r)
                else:
                    await mod_channel.send("A moderator can only review one report at a time.")

            elif message.content == ModReview.REVIEW_DONE:

                author_id = message.author.id
                if author_id in self.mod_review:
                    finished_report = self.mod_review.pop(author_id)
                    await message.channel.send(f"Report {finished_report.report.get_report_id()} is finished with review")
                else:
                    await message.channel.send("You don't have any active reports being reviewed") 

            else:
                # Check 
                pass
                
        return

    
    def eval_text(self, message):
        data_payload = {}
        # Check if its misinformation via OpenAI
        conclusion, reason = self.openai.misinfo_detection(message)
        data_payload["llm_result"] = conclusion
        data_payload["llm_reason"] = reason
        if conclusion == MISINFO:
            misinfo_type = self.openai.get_misinfo_type(message)
            data_payload["llm_result_type"] = misinfo_type

        # Check if its misinformation via Google Fact Check API
        #conclusion, similar_msgs = self.claimbuster.get_matching_facts(message)
        conclusion, similar_msgs = self.googlefactcheck.get_matching_facts(message)
        data_payload["crowd_source_result"] = conclusion
        data_payload["crowd_source_examples"] = similar_msgs

        return data_payload

    
    def code_format(self, payload):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        all_text = []

        text = f"**LLM conclusion**: {payload['llm_result']}\n**LLM reason**: {payload['llm_reason']}\n"
        if "llm_result_type" in payload:
            text += f"**LLM Misinformation Type**: {payload['llm_result_type']}\n"

        text += f"**Crowd Source Fact Check conclusion**: {payload['crowd_source_result']}\nHere are similar fact-checked statements from Google FactCheck API that support this decision: \n"
        for example in payload["crowd_source_examples"]:
            text += f"• {example['formatted_msg']}\n"

        all_text.append(text)

        aux_info = ""
        if payload['llm_result'] == payload['crowd_source_result']:
            all_text.append(f"\nThis post is likely {payload['llm_result']} based on agreement between multiple sources.")
            if payload['llm_result'] == MISINFO:
                all_text.append("-DELETE-")
                all_text.append(f"*Remove offending post*")
        else:
            all_text.append(f"\nIt is unclear whether this post is misinformation, please evaluate as necessary.")

        return all_text


client = ModBot()
client.run(discord_token)
