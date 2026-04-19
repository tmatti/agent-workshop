import json
import os
from datetime import datetime

from llm_client import generate_response, generate_response_with_tools

NAME = "Invoice Processor"

MODEL = "openrouter/openai/gpt-4o"

SYSTEM_PROMPT = """You are an Invoice Processing Agent specialized in handling invoices efficiently.

For each invoice you receive, call tools in this exact order:
1. extract_invoice_data — parse the raw text into structured fields
2. categorize_expenditure — pass a one-sentence description of what was purchased
3. check_purchasing_rules — pass the full invoice_data object returned by step 1
4. store_invoice — pass invoice_data, the category from step 2, and validation from step 3
5. Return a concise summary of the invoice number, category, and compliance status"""

tools = [
    {
        "type": "function",
        "function": {
            "name": "extract_invoice_data",
            "description": "Extract structured data from raw invoice text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "invoice_text": {"type": "string", "description": "Raw invoice text to parse"}
                },
                "required": ["invoice_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "categorize_expenditure",
            "description": "Classify an invoice into one of 20 spending categories based on a one-sentence description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "One-sentence summary of the expenditure"}
                },
                "required": ["description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_purchasing_rules",
            "description": "Validate an invoice against company purchasing policies. Returns compliant (bool) and issues (str).",
            "parameters": {
                "type": "object",
                "properties": {
                    "invoice_data": {
                        "type": "object",
                        "description": "Extracted invoice details including vendor, amount, and line items",
                    }
                },
                "required": ["invoice_data"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "store_invoice",
            "description": "Save processed invoice data to the out/ directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "invoice_data": {"type": "object", "description": "Extracted invoice data"},
                    "category": {"type": "string", "description": "Expenditure category"},
                    "validation": {"type": "object", "description": "Compliance validation result"},
                },
                "required": ["invoice_data", "category", "validation"],
            },
        },
    },
]


def extract_invoice_data(invoice_text: str) -> dict:
    response = generate_response(
        messages=[
            {
                "role": "system",
                "content": "Extract invoice data as JSON with fields: invoice_number, date, vendor, total_amount, line_items (list of {description, quantity, total}). Respond with only valid JSON.",
            },
            {"role": "user", "content": invoice_text},
        ],
        model=MODEL,
    )
    try:
        text = response.strip()
        if "```" in text:
            text = text.split("```")[1].strip()
            if text.startswith("json"):
                text = text[4:].strip()
        return json.loads(text)
    except Exception:
        return {"raw": response}


def categorize_expenditure(description: str) -> str:
    categories = [
        "Office Supplies", "IT Equipment", "Software Licenses", "Consulting Services",
        "Travel Expenses", "Marketing", "Training & Development", "Facilities Maintenance",
        "Utilities", "Legal Services", "Insurance", "Medical Services", "Payroll",
        "Research & Development", "Manufacturing Supplies", "Construction", "Logistics",
        "Customer Support", "Security Services", "Miscellaneous",
    ]
    return generate_response(
        messages=[
            {
                "role": "system",
                "content": f"You are a senior financial analyst. Classify the expense into exactly one of these categories and respond with only the category name:\n{categories}",
            },
            {"role": "user", "content": description},
        ],
        model=MODEL,
    ).strip()


def check_purchasing_rules(invoice_data: dict = None) -> dict:
    if not invoice_data:
        return {"compliant": False, "issues": "No invoice data provided for validation."}
    rules_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "config", "purchasing_rules.txt")
    )
    try:
        with open(rules_path) as f:
            purchasing_rules = f.read()
    except FileNotFoundError:
        purchasing_rules = "No rules available. Assume all invoices are compliant."

    response = generate_response(
        messages=[
            {
                "role": "system",
                "content": 'You are a corporate procurement compliance officer. Respond with only valid JSON in the format: {"compliant": true/false, "issues": "explanation or none"}',
            },
            {
                "role": "user",
                "content": f"Invoice data:\n{json.dumps(invoice_data, indent=2)}\n\nPurchasing rules:\n{purchasing_rules}\n\nIs this invoice compliant?",
            },
        ],
        model=MODEL,
    )
    try:
        text = response.strip()
        if "```" in text:
            text = text.split("```")[1].strip()
            if text.startswith("json"):
                text = text[4:].strip()
        return json.loads(text)
    except Exception:
        return {"compliant": True, "issues": response}


def store_invoice(invoice_data: dict, category: str, validation: dict) -> str:
    os.makedirs("out", exist_ok=True)
    invoice_number = invoice_data.get("invoice_number", "unknown")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"out/invoice_{invoice_number}_{timestamp}.json"
    record = {"invoice": invoice_data, "category": category, "validation": validation}
    with open(filename, "w") as f:
        json.dump(record, f, indent=2)
    return filename


tool_functions = {
    "extract_invoice_data": extract_invoice_data,
    "categorize_expenditure": categorize_expenditure,
    "check_purchasing_rules": check_purchasing_rules,
    "store_invoice": store_invoice,
}


def run() -> None:
    print("\nPaste invoice text (end with a blank line):")
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    invoice_text = "\n".join(lines)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Process this invoice:\n\n{invoice_text}"},
    ]

    for _ in range(20):
        print("Agent thinking...")
        message = generate_response_with_tools(messages, tools, model=MODEL)

        if not message.tool_calls:
            print(f"\n{message.content}")
            break

        messages.append(message)
        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            print(f"  -> {name}({list(args.keys())})")
            result = tool_functions[name](**args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })
