from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, SessionStarted, ActionExecuted


class ActionCheckSufficientFunds(Action):
    def name(self) -> Text:
        return "action_check_sufficient_funds"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        # hard-coded balance for tutorial purposes. in production this
        # would be retrieved from a database or an API
        balance = 1000
        transfer_amount = tracker.get_slot("amount")
        has_sufficient_funds = transfer_amount <= balance
        return [SlotSet("has_sufficient_funds", has_sufficient_funds)]

class ActionSessionStart(Action):
    """Executes at start of session"""

    def name(self) -> Text:
        """Unique identifier of the action"""
        return "action_session_start"

    @staticmethod
    def _slot_set_events_from_tracker(
        tracker: "Tracker",
    ) -> List["SlotSet"]:
        """Fetches SlotSet events from tracker and carries over keys and values"""

        # when restarting most slots should be reset, except for the these
        relevant_slots = []

        return [
            SlotSet(
                key=event.get("name"),
                value=event.get("value"),
            )
            for event in tracker.events
            if event.get("event") == "slot" and event.get("name") in relevant_slots
        ]

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        """Executes the custom action"""
        # the session should begin with a `session_started` event
        events = [SessionStarted()]

        
        
        users = {"name": "James", 
                 "address_line_1": "300 Lakeside Ave",
                 "city": "Seattle",
                 "state": "WA",
                 "zip_code": "98112"
                }
        
        events.append(SlotSet("address_line_1", users.get("address_line_1")))
        events.append(SlotSet("city", users.get("city")))
        events.append(SlotSet("state", users.get("state")))
        events.append(SlotSet("zip_code",users.get("zip_code")))

        events.append(ActionExecuted("action_listen"))
        return events

class TransactionSearch(Action):

    def name(self) -> str:
        return "transaction_search"
    
    def get_transactions(self):
        transactions = [
            {
              "datetime": "16th July",
              "recipient": "Mexicali",
              "amount": "30$",
              "description": "taco tuesday"
            },
            {
              "datetime": "10th June",
              "recipient": "Macy's",
              "amount": "700$",
              "description": "miscelleanous shopping"
            },
            {
              "datetime": "16th May",
              "recipient": "Trader Joe's",
              "amount": "50$",
              "description": "weekly groceries"
            }
        ]
        return transactions
               
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[str, Any]):
        transactions = [self.get_transactions()[0]]
        transactions_list = [f"{t['amount']} to {t['recipient']} at {t['datetime']} for {t['description']}" for t in transactions]
        return [SlotSet("transactions_list", transactions_list)]