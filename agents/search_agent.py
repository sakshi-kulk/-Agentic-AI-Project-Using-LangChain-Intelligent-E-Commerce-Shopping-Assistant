"""Requirement extraction and product search agent."""

import os
import re
from typing import Any

from tools.product_search_tool import search_products


def extract_requirements(customer_requirement: str, preferred_ram: str = "") -> dict[str, Any]:
    extracted: dict[str, Any] = {
        "use_case": customer_requirement.strip(),
        "preferred_ram": preferred_ram.strip(),
    }
    if os.getenv("OPENAI_API_KEY"):
        try:
            from langchain_openai import ChatOpenAI

            response = ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0
            ).invoke(
                "Extract the user's computer use case and preferred RAM in GB. "
                "Return only JSON with keys use_case and preferred_ram. Request: "
                + customer_requirement
            )
            import json

            parsed = json.loads(str(response.content))
            extracted["use_case"] = str(parsed.get("use_case") or extracted["use_case"])
            extracted["preferred_ram"] = str(
                parsed.get("preferred_ram") or extracted["preferred_ram"]
            )
        except Exception:
            pass
    if not extracted["preferred_ram"]:
        match = re.search(r"\b(8|16|24|32|64)\s*gb\b", customer_requirement, re.I)
        extracted["preferred_ram"] = f"{match.group(1)}GB" if match else ""
    return extracted


def run_search_agent(
    customer_requirement: str,
    budget: float,
    preferred_ram: str = "",
) -> list[dict]:
    requirements = extract_requirements(customer_requirement, preferred_ram)
    return search_products(budget, requirements["use_case"], requirements["preferred_ram"])