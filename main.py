
import openai
import requests
import json
import time
import os
from datetime import datetime, timedelta

# Load environment variables - ensure these are set in your Replit Secrets
if not os.environ.get("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is not set")
if not os.environ.get("CALCOM_API_KEY"):
    raise ValueError("CALCOM_API_KEY environment variable is not set")
if not os.environ.get("ASSISTANT_ID"):
    raise ValueError("ASSISTANT_ID environment variable is not set")

openai.api_key = os.environ.get("OPENAI_API_KEY")
CALCOM_API_KEY = os.environ.get("CALCOM_API_KEY")
CALCOM_BASE_URL = "https://api.cal.com/v1/slots"

def fetch_calcom_slots_dynamic():
    """
    Fetches available slots for the next 7 days from Cal.com API.
    """
    event_slug = "discovery"
    start_time = datetime.now().strftime("%Y-%m-%d")
    end_time = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    event_type_id = "859968"

    query_params = {
        "apiKey": CALCOM_API_KEY,
        "eventTypeSlug": event_slug,
        "startTime": start_time,
        "endTime": end_time,
        "eventTypeId": event_type_id,
    }

    try:
        print("Fetching available slots from Cal.com...")
        response = requests.get(CALCOM_BASE_URL, params=query_params)
        response.raise_for_status()
        slots_data = response.json()

        slots = []
        for date, times in slots_data.get("slots", {}).items():
            for time_entry in times:
                slots.append({"date": date, "time": time_entry["time"]})

        return slots if slots else [{"message": "No available slots found"}]

    except requests.exceptions.RequestException as e:
        return [{"error": f"Error fetching slots: {e}"}]

def test_assistant_function():
    assistant_id = os.environ.get("ASSISTANT_ID")

    print("Creating a test thread...")
    thread = openai.beta.threads.create()
    thread_id = thread.id

    print("Sending a test message to the assistant...")
    openai.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content="Fetch available appointment slots for the next 7 days."
    )

    print("Running the assistant...")
    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )

    while True:
        run = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        print(f"Current run status: {run.status}")
        if run.status == "requires_action":
            steps = openai.beta.threads.runs.steps.list(thread_id=thread_id, run_id=run.id)
            for step in steps.data:
                if step.step_details.type == "tool_calls":
                    for tool_call in step.step_details.tool_calls:
                        print(f"Executing function: {tool_call.function.name}")
                        if tool_call.function.name == "fetch_calcom_slots_dynamic":
                            result = fetch_calcom_slots_dynamic()
                            print("Function Result:", result)

                            print("Submitting function result...")
                            openai.beta.threads.runs.submit_tool_outputs(
                                thread_id=thread_id,
                                run_id=run.id,
                                tool_outputs=[{
                                    "tool_call_id": tool_call.id,
                                    "output": json.dumps(result)
                                }]
                            )
                            print("Function result submitted successfully.")
                            break
            break
        elif run.status in ["completed", "failed"]:
            print(f"Run status: {run.status}")
            break
        time.sleep(2)

    while True:
        run = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run.status == "completed":
            print("Assistant run completed. Fetching assistant response...")
            messages = openai.beta.threads.messages.list(thread_id=thread_id)
            for message in messages.data:
                if message.role == "assistant":
                    print("Assistant Response:")
                    print(message.content[0].text.value)
            break
        elif run.status == "failed":
            print("Assistant run failed.")
            break
        time.sleep(2)

if __name__ == "__main__":
    test_assistant_function()
