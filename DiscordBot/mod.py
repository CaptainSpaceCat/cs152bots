from enum import Enum, auto

from report import ReportView, ReportDropdown
# TODO: move these to constants.py folder
from report import GENERIC_YES, GENERIC_NO

# System Prompts
ACCURATE_LINK_PROMPT = "Does the report contain a factual link?"
MISINFO_VIOLATION_PROMPT = "Is the reported post in violation of our misinformation policy?"
ADVERSARIAL_PROMPT = "Is the report an adversarial user report?"
IMMEDIATE_DANGER_PROMPT = "Does this post pose an immediate threat via potential to cause harm?"
REPEAT_OFFENDER_PROMPT = "Does the account being reported have a history of 3 or more violations?"

# System warnings

class ReviewState(Enum):
    REVIEW_START = auto()
    REVIEW_COMPLETE = auto()

class ModReview:

    LIST_REPORTS = "list-reports"
    REVIEW_URGENT_REPORT = "review-urgent-report"
    REVIEW_DONE = "finish-report"

    # TODO: allow for review of arbitrary report where the UUID of the report is specified
    REVIEW_REPORT = "review-report"

    def __init__(self, client, report):
        self.client = client
        self.report = report
        self.review_status = ReviewState.REVIEW_START
        self.channel = None
 
    @staticmethod
    def list_reports(reports):
        all_reports = ""
        for ind, report in enumerate(reports):
            all_reports += f"(#{ind}) -- ID: {report.get_report_id()}, Sev: {report.get_report_severity()}, Date: {report.get_report_date()}\n"
        return all_reports


    async def handle_message(self, message):

        yes_no_select_options = [
            (GENERIC_YES, ""),
            (GENERIC_NO, "")
        ]
        if message.content == self.REVIEW_URGENT_REPORT:
            # Print out the full report
            self.channel = message.channel
            full_report = self.report.get_formatted_report()
            await message.channel.send(f"This is the full report transcript:\n\n {full_report}")
            
            return [(ACCURATE_LINK_PROMPT, ReportView(yes_no_select_options, ACCURATE_LINK_PROMPT, self._handle_report_type))]
            
        return []
    
    
    async def _handle_report_type(self, prompt, payload):
        yes_no_select_options = [
            (GENERIC_YES, ""),
            (GENERIC_NO, "")
        ]

        if prompt == ACCURATE_LINK_PROMPT:
            if payload == GENERIC_NO:
                # TODO: Implement warn the user
                await self.channel.send(f"*Warn offending user*")
                
            return [(MISINFO_VIOLATION_PROMPT, ReportView(yes_no_select_options, MISINFO_VIOLATION_PROMPT, self._handle_report_type))]

        if prompt == MISINFO_VIOLATION_PROMPT:
            if payload == GENERIC_YES:
                # TODO: remove the post
                await self.channel.send(f"*Remove offending post*")
                return [(IMMEDIATE_DANGER_PROMPT, ReportView(yes_no_select_options, IMMEDIATE_DANGER_PROMPT, self._handle_report_type))]
            elif payload == GENERIC_NO:
                return [(ADVERSARIAL_PROMPT, ReportView(yes_no_select_options, ADVERSARIAL_PROMPT, self._handle_report_type))]

        if prompt == ADVERSARIAL_PROMPT:
            if payload == GENERIC_YES:
                # TODO: temporary ban on reporting
                await self.channel.send(f"*Temp ban on reporting*")
            elif payload == GENERIC_NO:
                # No further action
                pass

        if prompt == IMMEDIATE_DANGER_PROMPT:
            if payload == GENERIC_YES:
                # TODO: report to law enforcement
                # TODO: ban account
                await self.channel.send(f"*Report to law enforcement*")
                await self.channel.send(f"*Ban account*")
    
            elif payload == GENERIC_NO:
                return [(REPEAT_OFFENDER_PROMPT, ReportView(yes_no_select_options, REPEAT_OFFENDER_PROMPT, self._handle_report_type))]

        if prompt == REPEAT_OFFENDER_PROMPT:
            if payload == GENERIC_YES:
                # TODO: ban reported account
                await self.channel.send(f"*Report to law enforcement*")
            elif payload == GENERIC_NO:
                # TODO: Warn reported account
                await self.channel.send(f"*Warn account*")
            
        self.review_status = ReviewState.REVIEW_COMPLETE
        return [(f"Report remediation workflow finished. Type '{self.REVIEW_DONE}' to finish the report.")]