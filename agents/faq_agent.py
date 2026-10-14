"""Product FAQ RAG agent."""

from tools.faq_tool import answer_product_faq


def run_faq_agent(products: list[dict], questions: list[str] | None = None) -> dict[str, str]:
    question = " ".join(questions) if questions else (
        "Summarize the supported information about Python programming, introductory "
        "machine learning, typical battery runtime, and warranty."
    )
    answers: dict[str, str] = {}
    for product in products[:3]:
        product_id = str(product["product_id"])
        try:
            answers[product_id] = answer_product_faq(question, product)
        except Exception as error:
            answers[product_id] = f"FAQ retrieval unavailable: {error}"
    return answers