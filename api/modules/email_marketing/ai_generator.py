"""AI Email Generator — generates professional HTML emails from natural language (ADR-010)."""

import logging
import os
import re

import httpx

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sei un esperto di email marketing B2B italiano. Generi email HTML professionali, responsive e moderne.

REGOLE:
1. Output SOLO HTML valido — nessun testo prima o dopo il tag <div>
2. Layout responsive con max-width: 600px, centrato, font-family: -apple-system, BlinkMacSystemFont, sans-serif
3. Colori brand: primario #863bff (viola), testo #1a1a2e, sfondo #f9fafb
4. Struttura: header con logo "AF" viola → titolo → corpo testo → bottone CTA → firma → footer
5. Bottone CTA: background #863bff, color white, border-radius 10px, padding 14px 32px, text-decoration none, font-weight 600
6. Footer: "Questa email e stata inviata da {{azienda}}" in grigio chiaro, font-size 12px
7. Usa variabili con doppia graffa: {{nome}}, {{azienda}}, {{deal_name}}, {{commerciale}}, {{deal_value}}
8. PRIMA RIGA: commento HTML con subject line: <!-- subject: La tua subject line qui -->
9. Tono: professionale ma caldo, italiano formale (Lei)
10. NO immagini esterne, NO JavaScript, NO <style> tag — tutto inline CSS
11. Ogni paragrafo: color #555, font-size 16px, line-height 1.6
12. Header: div con background #863bff, padding 20px, text-align center, con testo "AF" in bianco bold"""


def sanitize_email_html(html: str) -> str:
    """Remove potentially dangerous HTML from AI output."""
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'\s+on\w+="[^"]*"', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<img[^>]+src="https?://[^"]*"[^>]*>', '', html, flags=re.IGNORECASE)
    return html.strip()


def extract_subject(html: str) -> tuple[str, str]:
    """Extract subject from <!-- subject: ... --> comment and return (subject, html_without_comment)."""
    match = re.search(r'<!--\s*subject:\s*(.+?)\s*-->', html, re.IGNORECASE)
    if match:
        subject = match.group(1).strip()
        clean_html = html[:match.start()] + html[match.end():]
        return subject, clean_html.strip()
    return "Email da AgentFlow", html


def detect_variables(html: str) -> list[str]:
    """Detect {{variable}} placeholders in HTML."""
    return sorted(set(re.findall(r'\{\{(\w+)\}\}', html)))


async def generate_email_html(
    prompt: str,
    tenant_name: str = "",
    user_name: str = "",
    contact_name: str = "",
    deal_name: str = "",
    tone: str = "professionale",
) -> dict:
    """Generate professional HTML email from natural language prompt."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return {"error": "OpenAI non configurato"}

    user_prompt = f"""Crea un'email per: {prompt}

CONTESTO:
- Azienda mittente: {tenant_name or 'non specificata'}
- Commerciale: {user_name or 'non specificato'}
- Destinatario: {contact_name or 'generico (usa {{{{nome}}}})'}
- Deal/Progetto: {deal_name or 'non specificato'}
- Tono: {tone}

VARIABILI DISPONIBILI (inseriscile dove appropriato):
{{{{nome}}}}, {{{{azienda}}}}, {{{{deal_name}}}}, {{{{commerciale}}}}, {{{{deal_value}}}}"""

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)

        # Clean up: extract HTML if wrapped in markdown code block
        if "```html" in content:
            content = content.split("```html")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        # Sanitize
        html = sanitize_email_html(content)

        # Extract subject
        subject, html = extract_subject(html)

        # Detect variables
        variables = detect_variables(html)

        return {
            "subject": subject,
            "html_body": html,
            "variables_detected": variables,
            "tokens_used": tokens_in + tokens_out,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "model": "gpt-4o-mini",
        }

    except httpx.HTTPStatusError as e:
        logger.error("OpenAI API error: %s", e.response.text)
        return {"error": f"Errore OpenAI: {e.response.status_code}"}
    except Exception as e:
        logger.error("Email generation failed: %s", e)
        return {"error": f"Errore generazione: {str(e)}"}


async def refine_email_html(
    html_body: str,
    instruction: str,
) -> dict:
    """Refine existing email HTML with a specific instruction."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return {"error": "OpenAI non configurato"}

    user_prompt = f"""Modifica questa email HTML seguendo l'istruzione.

ISTRUZIONE: {instruction}

EMAIL ATTUALE:
{html_body}

REGOLE: mantieni lo stesso stile, layout e variabili {{{{...}}}}. Output SOLO HTML modificato con <!-- subject: ... --> nella prima riga."""

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.5,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        if "```html" in content:
            content = content.split("```html")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        html = sanitize_email_html(content)
        subject, html = extract_subject(html)
        variables = detect_variables(html)

        return {
            "subject": subject,
            "html_body": html,
            "variables_detected": variables,
            "tokens_used": usage.get("total_tokens", 0),
            "model": "gpt-4o-mini",
        }

    except Exception as e:
        logger.error("Email refinement failed: %s", e)
        return {"error": f"Errore modifica: {str(e)}"}
