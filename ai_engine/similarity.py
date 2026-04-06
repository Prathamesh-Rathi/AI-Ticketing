# backend/ai_engine/similarity.py

import re
from sqlalchemy.orm import Session
from app import models


def extract_keywords(text: str) -> set:
    stop_words = {
        "the","a","an","is","it","in","on","at","to","for","of","and",
        "or","but","with","this","that","my","i","we","our","your","have",
        "has","was","were","am","are","be","been","being","do","does","did",
        "not","no","can","cant","could","would","should","will","get","got",
        "im","ive","its","hi","hello","please","thanks","thank","need","help"
    }
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    return {w for w in words if w not in stop_words}


def find_similar_tickets(
    title: str,
    body: str,
    category: str,
    db: Session,
    exclude_ticket_id: int = None,
    limit: int = 3
) -> list:
    query = db.query(models.Ticket).join(models.AIAnalysis).filter(
        models.Ticket.status.in_(["Resolved", "Closed"]),
        models.AIAnalysis.category == category
    )
    if exclude_ticket_id:
        query = query.filter(models.Ticket.id != exclude_ticket_id)

    candidates = query.limit(50).all()

    if not candidates:
        query2 = db.query(models.Ticket).filter(
            models.Ticket.status.in_(["Resolved", "Closed"])
        )
        if exclude_ticket_id:
            query2 = query2.filter(models.Ticket.id != exclude_ticket_id)
        candidates = query2.limit(50).all()

    if not candidates:
        return []

    new_keywords = extract_keywords(f"{title} {body}")

    scored = []
    for ticket in candidates:
        ticket_keywords = extract_keywords(f"{ticket.title} {ticket.body}")
        if not ticket_keywords:
            continue

        intersection = new_keywords & ticket_keywords
        union        = new_keywords | ticket_keywords
        similarity   = len(intersection) / len(union) if union else 0

        category_boost = 0
        if ticket.ai_analysis and ticket.ai_analysis.category == category:
            category_boost = 0.2

        final_score = round((similarity + category_boost) * 100)

        if final_score > 10:
            scored.append({
                "id":              ticket.id,
                "title":           ticket.title,
                "status":          ticket.status,
                "category":        ticket.ai_analysis.category if ticket.ai_analysis else "—",
                "severity":        ticket.ai_analysis.severity if ticket.ai_analysis else "—",
                "similarity":      final_score,
                "auto_response":   ticket.ai_analysis.auto_response if ticket.ai_analysis else None,
                "created_at":      ticket.created_at.strftime("%d %b %Y"),
                "shared_keywords": sorted(list(intersection))[:6]
            })

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:limit]