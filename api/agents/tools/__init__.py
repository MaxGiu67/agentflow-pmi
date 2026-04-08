"""Sales Agent v2 tools — LangChain tool functions organized by category.

Categories:
- CRM Core: deal CRUD, pipeline, contacts, activities
- Portal: resource search, projects, offers, timesheets
- Offer Generation: Word doc from template (python-docx)
- Search: resource matching by skill/seniority
"""

from api.agents.tools.offer_generator import generate_offer_document

__all__ = [
    "generate_offer_document",
]
