"""Rank eligible products against the customer's stated priorities."""


def rank_products(
    products: list[dict],
    inventory: dict[str, dict],
    budget_validation: dict[str, dict],
    preferred_ram: str = "",
) -> tuple[dict | None, str]:
    eligible = [
        product
        for product in products
        if inventory.get(str(product["product_id"]), {}).get("available")
        and budget_validation.get(str(product["product_id"]), {}).get("within_budget")
    ]
    if not eligible:
        if products and not any(
            inventory.get(str(product["product_id"]), {}).get("available") for product in products
        ):
            return None, "Matching laptops were found, but none are currently in stock."
        if products:
            return None, "Matching laptops were found, but none are within the stated budget."
        return None, "No laptops matched the budget and RAM preferences. Try a higher budget or a different RAM preference."

    requested_ram = "".join(character for character in preferred_ram if character.isdigit())

    def score(product: dict) -> tuple[float, float, float]:
        ram_match = bool(
            requested_ram
            and str(product["ram"]).split()[0].removesuffix("GB") == requested_ram
        )
        return (float(ram_match), float(product["rating"]), -float(product["price"]))

    winner = max(eligible, key=score)
    reason = (
        f"{winner['product_name']} is in stock and within budget at ₹{float(winner['price']):,.0f}. "
        f"It has {winner['ram']} RAM, {winner['storage']} storage, "
        f"{winner['battery_life']} listed battery life, and a {winner['rating']}/5 rating."
    )
    return winner, reason