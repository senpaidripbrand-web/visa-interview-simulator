"""
DS-160 Visa Application PDF Parser & Personalized Question Generator.

Extracts key applicant information from a DS-160 confirmation PDF using
pdfplumber + regex, and generates tailored interview questions based on
the applicant's profile.
"""

import re
from datetime import datetime, date

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def extract_profile(pdf_path):
    """
    Extract key fields from a DS-160 PDF.

    Args:
        pdf_path: Path to a DS-160 confirmation PDF.

    Returns:
        A dict with all extracted fields. Missing fields default to "" or None.
        Returns None if pdfplumber is unavailable or text cannot be extracted.
    """
    if pdfplumber is None:
        return None

    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception:
        return None

    if not text.strip():
        return None

    return _parse_fields(text)


def _parse_fields(text):
    """Run all regex parsers against the raw extracted text."""
    profile = {
        "surname": "",
        "given_names": "",
        "full_name": "",
        "nationality": "",
        "country": "",
        "date_of_birth": "",
        "age": None,
        "gender": "",
        "marital_status": "",
        "occupation": "",
        "employer": "",
        "monthly_income": "",
        "purpose_of_trip": "",
        "travel_start_date": "",
        "travel_end_date": "",
        "length_of_stay": "",
        "previous_us_travel": "",
        "previous_us_travel_details": "",
        "previous_refusals": "",
        "previous_refusal_details": "",
        "education_level": "",
        "education_institution": "",
        "address": "",
        "city": "",
        "visa_type": "",
        "trip_payer": "",
        "us_contact_name": "",
        "us_contact_relationship": "",
        "travel_companions": "",
        "previous_countries_visited": "",
        "family_in_us": "",
    }

    lower = text.lower()

    # ---- Surname ----
    m = _search(text,
        r"Surnames?\s*[:\-]?\s*([A-Z][A-Z\s\-']+)",
        r"Family\s+Name\s*[:\-]?\s*([A-Z][A-Z\s\-']+)",
        r"Last\s+Name\s*[:\-]?\s*([A-Z][A-Z\s\-']+)")
    if m:
        profile["surname"] = _clean(m.group(1))

    # ---- Given Names ----
    m = _search(text,
        r"Given\s+Names?\s*[:\-]?\s*([A-Z][A-Z\s\-']+)",
        r"First\s+Name\s*[:\-]?\s*([A-Z][A-Z\s\-']+)")
    if m:
        profile["given_names"] = _clean(m.group(1))

    # Full name
    parts = [p for p in (profile["surname"], profile["given_names"]) if p]
    profile["full_name"] = ", ".join(parts)

    # ---- Nationality / Country ----
    m = _search(text,
        r"Nationalit(?:y|ies)\s*[:\-]?\s*([A-Za-z][A-Za-z\s\-]+)",
        r"Country/?Region\s+of\s+Origin\s*[:\-]?\s*([A-Za-z][A-Za-z\s\-]+)",
        r"Citizenship\s*[:\-]?\s*([A-Za-z][A-Za-z\s\-]+)",
        r"Country\s+of\s+Citizenship\s*[:\-]?\s*([A-Za-z][A-Za-z\s\-]+)")
    if m:
        val = re.split(r"\b(?:Date|Gender|Marital|Sex)\b", m.group(1))[0]
        profile["nationality"] = _clean(val)
        profile["country"] = profile["nationality"]

    # ---- Date of Birth ----
    m = _search(text,
        r"Date\s+of\s+Birth\s*[:\-]?\s*(\d{1,2}[\s\-/]\w{3,9}[\s\-/]\d{4})",
        r"Date\s+of\s+Birth\s*[:\-]?\s*(\d{4}[\s\-/]\d{1,2}[\s\-/]\d{1,2})",
        r"Date\s+of\s+Birth\s*[:\-]?\s*(\d{1,2}[\s\-/]\d{1,2}[\s\-/]\d{4})",
        r"DOB\s*[:\-]?\s*(\d{1,2}[\s\-/]\w{3,9}[\s\-/]\d{4})")
    if m:
        dob = _clean(m.group(1))
        profile["date_of_birth"] = dob
        profile["age"] = _estimate_age(dob)

    # ---- Gender ----
    m = _search(text, r"(?:Sex|Gender)\s*[:\-]?\s*(Male|Female|M|F)\b")
    if m:
        v = m.group(1).strip().upper()
        profile["gender"] = "Male" if v in ("M", "MALE") else "Female"

    # ---- Marital Status ----
    m = _search(text,
        r"Marital\s+Status\s*[:\-]?\s*(Single|Married|Divorced|Widowed|Separated|Never\s+Married|Other)")
    if m:
        profile["marital_status"] = m.group(1).strip().title()

    # ---- Occupation ----
    m = _search(text,
        r"(?:Present|Primary)?\s*Occupation\s*[:\-]?\s*([^\n]+)",
        r"Job\s+Title\s*[:\-]?\s*([^\n]+)")
    if m:
        profile["occupation"] = _clean(m.group(1))

    # ---- Employer ----
    m = _search(text,
        r"Employer(?:\s+or\s+School)?\s+Name\s*[:\-]?\s*([^\n]+)",
        r"Name\s+of\s+Employer\s*[:\-]?\s*([^\n]+)",
        r"Company\s+Name\s*[:\-]?\s*([^\n]+)")
    if m:
        profile["employer"] = _clean(m.group(1))

    # ---- Monthly Income ----
    m = _search(text,
        r"Monthly\s+(?:Income|Salary)\s*[:\-]?\s*\$?\s*([\d,\.]+)",
        r"\bIncome\s*[:\-]?\s*\$?\s*([\d,\.]+)",
        r"\bSalary\s*[:\-]?\s*\$?\s*([\d,\.]+)")
    if m:
        profile["monthly_income"] = m.group(1).replace(",", "").strip()

    # ---- Purpose of trip ----
    m = _search(text,
        r"Purpose\s+of\s+Trip\s+to\s+the\s+U\.?S\.?\s*[:\-]?\s*([^\n]+)",
        r"Purpose\s+of\s+(?:Travel|Visit|Trip)\s*[:\-]?\s*([^\n]+)",
        r"Specific\s+Travel\s+Plans?\s*[:\-]?\s*([^\n]+)")
    if m:
        profile["purpose_of_trip"] = _clean(m.group(1))

    # ---- Travel dates ----
    m = _search(text,
        r"(?:Intended\s+)?Date\s+of\s+Arrival\s*[:\-]?\s*([\d\w\s\-/]+)",
        r"Arrival\s+Date\s*[:\-]?\s*([\d\w\s\-/]+)",
        r"Travel\s+Date\s*[:\-]?\s*([\d\w\s\-/]+)")
    if m:
        profile["travel_start_date"] = _clean(m.group(1))

    m = _search(text,
        r"(?:Intended\s+)?Date\s+of\s+Departure\s*[:\-]?\s*([\d\w\s\-/]+)",
        r"Departure\s+Date\s*[:\-]?\s*([\d\w\s\-/]+)")
    if m:
        profile["travel_end_date"] = _clean(m.group(1))

    m = _search(text,
        r"(?:Intended\s+)?Length\s+of\s+Stay\s*[:\-]?\s*([^\n]+)")
    if m:
        profile["length_of_stay"] = _clean(m.group(1))

    # ---- Previous US travel ----
    m = _search(text,
        r"Have\s+You\s+Ever\s+Been\s+(?:in\s+|to\s+)?the\s+U\.?S\.?\s*\??\s*[:\-]?\s*(Yes|No)",
        r"Previous\s+U\.?S\.?\s+Travel\s*[:\-]?\s*(Yes|No)")
    if m:
        profile["previous_us_travel"] = m.group(1).strip().title()
    elif "previously traveled to the u" in lower or "previous trip to u" in lower:
        profile["previous_us_travel"] = "Yes"

    m = _search(text,
        r"Date\s+of\s+(?:Last|Previous)\s+(?:Arrival|Visit)\s*[:\-]?\s*([^\n]+)")
    if m:
        profile["previous_us_travel_details"] = _clean(m.group(1))

    # ---- Previous refusals ----
    m = _search(text,
        r"(?:Have\s+You\s+Ever\s+Been\s+)?(?:Refused\s+a\s+(?:U\.?S\.?\s+)?Visa|Visa\s+Refused)\s*\??\s*[:\-]?\s*(Yes|No)",
        r"(?:Previously\s+)?Denied\s+a\s+U\.?S\.?\s+Visa\s*\??\s*[:\-]?\s*(Yes|No)")
    if m:
        profile["previous_refusals"] = m.group(1).strip().title()
    elif "214(b)" in lower or "previously refused" in lower:
        profile["previous_refusals"] = "Yes"

    m = _search(text,
        r"(?:Refusal|Denial)\s+(?:Date|Details?|Explanation)\s*[:\-]?\s*([^\n]+)")
    if m:
        profile["previous_refusal_details"] = _clean(m.group(1))

    # ---- Education ----
    m = _search(text,
        r"(?:Highest\s+)?(?:Level\s+of\s+)?Education(?:al)?\s*(?:Level)?\s*[:\-]?\s*([^\n]+)")
    if m:
        profile["education_level"] = _clean(m.group(1))

    m = _search(text,
        r"(?:Name\s+of\s+)?(?:School|University|College|Institution)\s+Name\s*[:\-]?\s*([^\n]+)")
    if m:
        profile["education_institution"] = _clean(m.group(1))

    # ---- Address / City ----
    m = _search(text,
        r"(?:Home\s+)?Address(?:\s+Line\s*1)?\s*[:\-]?\s*([^\n]+)")
    if m:
        profile["address"] = _clean(m.group(1))

    m = _search(text, r"City\s*[:\-]?\s*([A-Za-z][A-Za-z\s\-]+)")
    if m:
        v = re.split(r"\b(?:State|Province|Postal|ZIP|Country)\b", m.group(1))[0]
        profile["city"] = _clean(v)

    # ---- Visa type ----
    m = _search(text,
        r"Visa\s+(?:Class|Type|Category)\s*[:\-]?\s*([A-Z][A-Z0-9/\-]*)",
        r"Type\s+of\s+Visa\s*[:\-]?\s*([A-Z][A-Z0-9/\-]*)",
        r"\b(B[\-]?1/?B?2?|B[\-]?2|F[\-]?1|J[\-]?1|H[\-]?1B|L[\-]?1|O[\-]?1|K[\-]?1)\b")
    if m:
        profile["visa_type"] = _clean(m.group(1))

    # ---- Trip payer ----
    m = _search(text,
        r"(?:Who\s+(?:is|will\s+be)\s+)?Pay(?:ing|er)\s+(?:for\s+(?:Your|the)\s+Trip)?\s*[:\-]?\s*([^\n]+)",
        r"Person\s+Paying\s+for\s+Trip\s*[:\-]?\s*([^\n]+)",
        r"Trip\s+(?:will\s+be\s+)?(?:Paid|Funded)\s+by\s*[:\-]?\s*([^\n]+)")
    if m:
        profile["trip_payer"] = _clean(m.group(1))

    # ---- US contact ----
    m = _search(text,
        r"(?:U\.?S\.?\s+)?(?:Point\s+of\s+)?Contact(?:\s+Person)?\s+(?:in\s+(?:the\s+)?U\.?S\.?)?\s*(?:Name)?\s*[:\-]?\s*([^\n]+)",
        r"Contact\s+(?:Person|Name)\s+in\s+(?:the\s+)?U\.?S\.?\s*[:\-]?\s*([^\n]+)")
    if m:
        profile["us_contact_name"] = _clean(m.group(1))

    m = _search(text,
        r"Relationship\s+to\s+(?:You|Applicant)\s*[:\-]?\s*([^\n]+)")
    if m:
        profile["us_contact_relationship"] = _clean(m.group(1))

    # ---- Travel companions ----
    m = _search(text,
        r"(?:Are\s+there\s+other\s+persons\s+traveling\s+with\s+you|Travel(?:ing)?\s+Companions?)\s*\??\s*[:\-]?\s*([^\n]+)",
        r"Traveling\s+With\s*[:\-]?\s*([^\n]+)")
    if m:
        profile["travel_companions"] = _clean(m.group(1))

    # ---- Countries visited ----
    m = _search(text,
        r"Countries?\s+(?:You\s+Have\s+)?Visited\s*(?:in\s+the\s+Last\s+\d+\s+Years?)?\s*[:\-]?\s*([^\n]+)",
        r"Countries?\s+(?:Traveled|Been)\s+(?:To)?\s*[:\-]?\s*([^\n]+)")
    if m:
        profile["previous_countries_visited"] = _clean(m.group(1))

    # ---- Family in US ----
    m = _search(text,
        r"(?:Do\s+you\s+have\s+)?(?:Immediate\s+)?(?:Family|Relatives?)\s+in\s+(?:the\s+)?U\.?S\.?\s*\??\s*[:\-]?\s*(Yes|No)")
    if m:
        profile["family_in_us"] = m.group(1).strip().title()

    return profile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _search(text, *patterns):
    """Try patterns in order, return first regex Match or None."""
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m
    return None


def _clean(value):
    """Trim whitespace and trailing punctuation from a parsed value."""
    if value is None:
        return ""
    val = str(value).strip()
    val = val.split("\n")[0].strip()
    val = val.rstrip(":-,;")
    return val


def _estimate_age(dob_str):
    """Estimate age in years from a DOB string. Returns None if unparsable."""
    if not dob_str:
        return None
    for fmt in (
        "%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%d-%B-%Y",
        "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%Y/%m/%d",
        "%d %b %y",
    ):
        try:
            dob = datetime.strptime(dob_str, fmt).date()
            today = date.today()
            return today.year - dob.year - (
                (today.month, today.day) < (dob.month, dob.day)
            )
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Personalized question generation
# ---------------------------------------------------------------------------

def generate_personalized_questions(profile):
    """
    Generate 15-20 tough, personalized visa interview questions based on
    the applicant's DS-160 profile.

    Each question is a dict with keys:
        text       - The interview question
        category   - e.g. "purpose", "ties", "finances", "immigration_intent"
        key        - Short snake_case identifier
        follow_ups - List of 2-3 follow-up question strings

    Args:
        profile: Dict returned by extract_profile().

    Returns:
        List of question dicts (typically 15-20 items).
    """
    if not profile:
        profile = {}

    def get(key):
        v = profile.get(key)
        return v.strip() if isinstance(v, str) else (v if v is not None else "")

    def low(key):
        v = get(key)
        return v.lower() if isinstance(v, str) else ""

    questions = []

    # ---------- 1. Universal: purpose ----------
    questions.append({
        "text": "What is the specific purpose of your trip to the United States?",
        "category": "purpose",
        "key": "trip_purpose",
        "follow_ups": [
            "Why did you choose the United States rather than another country?",
            "Walk me through your day-by-day itinerary.",
            "How long have you been planning this trip?",
        ],
    })

    # ---------- 2. Universal: employment ----------
    employer = get("employer")
    questions.append({
        "text": "What do you do for a living, and how long have you held this position?",
        "category": "employment",
        "key": "occupation_detail",
        "follow_ups": [
            f"Can you describe your responsibilities at {employer}?" if employer
                else "Can you describe your daily responsibilities?",
            "Do you have an employment letter or approved leave for this trip?",
            "Who will handle your duties while you are away?",
        ],
    })

    # ---------- 3. Universal: funding ----------
    questions.append({
        "text": "How will you fund your stay in the United States?",
        "category": "finances",
        "key": "funding_source",
        "follow_ups": [
            "Do you have bank statements showing your financial standing?",
            "What is your average monthly balance over the last six months?",
            "Are there any other sources of income or assets?",
        ],
    })

    # ---------- 4. Universal: ties ----------
    questions.append({
        "text": "What ties do you have to your home country that will compel you to return?",
        "category": "ties",
        "key": "home_ties",
        "follow_ups": [
            "Do you own property or run a business in your home country?",
            "Who depends on you financially back home?",
            "What commitments await you upon your return?",
        ],
    })

    # ---------- 5. Universal: travel plans ----------
    questions.append({
        "text": "When do you plan to depart and return, and where exactly will you stay?",
        "category": "travel_plans",
        "key": "travel_dates_accommodation",
        "follow_ups": [
            "Have you booked flights and accommodation already?",
            "Can you show me your hotel reservation or invitation letter?",
            "Why these specific dates?",
        ],
    })

    # ---------- Previous refusals ----------
    if low("previous_refusals") == "yes" or get("previous_refusal_details"):
        questions.append({
            "text": "You indicated you have been previously refused a U.S. visa. Can you explain what happened?",
            "category": "refusal_history",
            "key": "previous_refusal_explain",
            "follow_ups": [
                "What has changed in your circumstances since the refusal?",
                "Do you know under which section you were refused?",
                "Have you been refused a visa to any other country?",
            ],
        })
        questions.append({
            "text": "Why should your application be approved this time when it was denied before?",
            "category": "refusal_history",
            "key": "refusal_overcome",
            "follow_ups": [
                "What new evidence are you presenting today?",
                "How is your situation different now?",
            ],
        })

    # ---------- Low / missing income ----------
    income_str = get("monthly_income")
    low_income = False
    if income_str:
        try:
            if float(income_str.replace(",", "")) < 3000:
                low_income = True
        except ValueError:
            pass
    if low_income or not income_str:
        questions.append({
            "text": "Your declared income appears modest relative to the cost of travel. How can you afford this trip?",
            "category": "finances",
            "key": "low_income_funding",
            "follow_ups": [
                "Is someone else sponsoring your trip? What is their relationship to you?",
                "Can you provide evidence of savings or investments?",
                "Have you traveled internationally before on a similar budget?",
            ],
        })

    # ---------- Sponsor / trip payer ----------
    payer = low("trip_payer")
    if payer and "self" not in payer and payer not in ("", "n/a", "none"):
        questions.append({
            "text": "You indicated that someone else is paying for your trip. Who are they and why are they funding your travel?",
            "category": "finances",
            "key": "sponsor_relationship",
            "follow_ups": [
                "Can you provide an affidavit of support from your sponsor?",
                "What is your sponsor's occupation and income?",
                "How long have you known this person?",
            ],
        })

    # ---------- Young & unmarried ----------
    age = profile.get("age")
    marital = low("marital_status")
    if (age and isinstance(age, int) and age < 30) and (marital in ("single", "never married", "unmarried", "")):
        questions.append({
            "text": "You are young and unmarried. What strong ties keep you connected to your home country?",
            "category": "ties",
            "key": "young_single_ties",
            "follow_ups": [
                "Do you have a stable career or ongoing education at home?",
                "Do you have dependents or family obligations?",
                "Have you considered pursuing opportunities in the U.S. instead of returning?",
            ],
        })
        questions.append({
            "text": "Do you have any plans to study or work in the United States in the future?",
            "category": "immigration_intent",
            "key": "future_us_plans",
            "follow_ups": [
                "Have you ever applied for a student or work visa?",
                "Are you aware that working on a tourist visa is illegal?",
            ],
        })

    # ---------- Married ----------
    if marital == "married":
        questions.append({
            "text": "Is your spouse traveling with you? If not, why not?",
            "category": "ties",
            "key": "spouse_travel",
            "follow_ups": [
                "Who will care for your family while you are away?",
                "Do you have children, and where will they stay?",
                "Has your spouse ever applied for a U.S. visa?",
            ],
        })

    # ---------- Tourism ----------
    purpose = low("purpose_of_trip")
    if any(w in purpose for w in ("tourism", "tourist", "vacation", "pleasure", "visit")):
        questions.append({
            "text": "Why do you specifically want to visit the United States for tourism rather than other destinations?",
            "category": "purpose",
            "key": "tourism_why_us",
            "follow_ups": [
                "Which cities or attractions do you plan to visit?",
                "Have you traveled to other countries as a tourist before?",
                "How did you decide on this itinerary?",
            ],
        })

    # ---------- Business ----------
    if any(w in purpose for w in ("business", "conference", "meeting", "trade")):
        questions.append({
            "text": "Can you describe the specific business activities you will engage in during your trip?",
            "category": "purpose",
            "key": "business_activities",
            "follow_ups": [
                "Do you have a letter of invitation from the U.S. company?",
                "Will you receive any payment or compensation in the U.S.?",
                "What is your company's relationship with the U.S. entity?",
            ],
        })

    # ---------- Study ----------
    if any(w in purpose for w in ("study", "student", "education", "school")):
        questions.append({
            "text": "What program will you be studying and why did you choose this institution?",
            "category": "purpose",
            "key": "study_program",
            "follow_ups": [
                "How will you finance your tuition and living expenses?",
                "Do you plan to return home after completing your studies?",
                "Did you also apply to universities in your home country?",
            ],
        })

    # ---------- Family in US ----------
    if low("family_in_us") == "yes":
        questions.append({
            "text": "You have family members in the United States. Who are they and what is their immigration status?",
            "category": "immigration_intent",
            "key": "family_in_us_detail",
            "follow_ups": [
                "Have any of your family members petitioned for you to immigrate?",
                "How often do you visit them, and have you always returned on time?",
                "Are you financially dependent on your relatives in the U.S.?",
            ],
        })
        questions.append({
            "text": "Given that you have family in the U.S., how can you assure me you will return home?",
            "category": "ties",
            "key": "family_return_assurance",
            "follow_ups": [
                "What is more important to you at home than being near your U.S. family?",
                "Have you ever overstayed a visa in any country?",
            ],
        })

    # ---------- Previous US travel ----------
    if low("previous_us_travel") == "yes":
        questions.append({
            "text": "You have traveled to the U.S. before. When was your last visit and did you comply with the visa terms?",
            "category": "travel_history",
            "key": "previous_us_compliance",
            "follow_ups": [
                "How long did you stay and what did you do during that visit?",
                "Did you ever overstay or violate any visa conditions?",
                "Why are you applying for a new visa now?",
            ],
        })
    else:
        questions.append({
            "text": "You have never visited the United States before. Why now?",
            "category": "purpose",
            "key": "first_time_us_why",
            "follow_ups": [
                "What other countries have you visited?",
                "Did something specific trigger this trip?",
            ],
        })

    # ---------- Self-employed / unemployed / student ----------
    occupation = low("occupation")
    if "student" in occupation or "unemployed" in occupation or not occupation:
        questions.append({
            "text": "How do you support yourself financially given your current employment situation?",
            "category": "finances",
            "key": "no_income_support",
            "follow_ups": [
                "Who pays for your daily expenses?",
                "What are your plans after completing your current studies or job search?",
                "Do you have any job offers waiting at home?",
            ],
        })
    if "self" in occupation or "entrepreneur" in occupation or "freelan" in occupation:
        questions.append({
            "text": "As a self-employed individual, can you demonstrate consistent income and business stability?",
            "category": "finances",
            "key": "self_employed_stability",
            "follow_ups": [
                "Do you have tax returns or business registration documents?",
                "Who will manage your business while you are away?",
                "How long has your business been operating?",
            ],
        })

    # ---------- Travel companions ----------
    companions = low("travel_companions")
    if companions and companions not in ("no", "none", "n/a"):
        questions.append({
            "text": "Who are you traveling with and what is your relationship to them?",
            "category": "travel_plans",
            "key": "companions_detail",
            "follow_ups": [
                "Are your companions also applying for visas?",
                "Have any of them been refused a visa before?",
                "Will you all stay at the same location?",
            ],
        })

    # ---------- Countries visited ----------
    countries = get("previous_countries_visited")
    if countries:
        questions.append({
            "text": "You have traveled to other countries. Which ones, and did you comply with all visa conditions?",
            "category": "travel_history",
            "key": "intl_travel_history",
            "follow_ups": [
                "Were any of those trips for purposes similar to this one?",
                "Did you return on time from all of those trips?",
                "Do you currently hold valid visas for other countries?",
            ],
        })
    else:
        questions.append({
            "text": "Have you traveled internationally before? If not, why is the U.S. your first destination?",
            "category": "travel_history",
            "key": "no_travel_history",
            "follow_ups": [
                "Why didn't you start with a closer or easier destination?",
                "Do you hold a valid passport from your country?",
            ],
        })

    # ---------- US contact ----------
    if get("us_contact_name"):
        contact = get("us_contact_name")
        relationship = get("us_contact_relationship") or "contact"
        questions.append({
            "text": f"Tell me about your {relationship} in the U.S. How do you know {contact}?",
            "category": "ties",
            "key": "us_contact_detail",
            "follow_ups": [
                "How long have you known this person?",
                "What is their immigration status?",
                "Will they be financially supporting you during your stay?",
            ],
        })

    # ---------- Catch-all immigration intent ----------
    questions.append({
        "text": "Do you have any intention of remaining in the United States beyond the approved period?",
        "category": "immigration_intent",
        "key": "overstay_intent",
        "follow_ups": [
            "What would happen to your job, family, or property if you did not return?",
            "Are you aware of the consequences of overstaying a U.S. visa?",
            "Have you ever been out of status in any country?",
        ],
    })

    # ---------- Closing ----------
    questions.append({
        "text": "Is there anything else you would like to tell me that supports your application?",
        "category": "closing",
        "key": "closing_statement",
        "follow_ups": [
            "Do you have any additional documents you would like to present?",
            "Is there anything about your situation I should understand better?",
        ],
    })

    return questions


# ---------------------------------------------------------------------------
# CLI convenience
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python ds160_parser.py <path_to_ds160.pdf>")
        sys.exit(1)

    profile = extract_profile(sys.argv[1])
    if profile is None:
        print("Failed to extract profile from PDF.")
        sys.exit(1)

    print("=" * 60)
    print("EXTRACTED DS-160 PROFILE")
    print("=" * 60)
    print(json.dumps(profile, indent=2, default=str))

    questions = generate_personalized_questions(profile)
    print("\n" + "=" * 60)
    print(f"PERSONALIZED INTERVIEW QUESTIONS ({len(questions)})")
    print("=" * 60)
    for i, q in enumerate(questions, 1):
        print(f"\n[{i}] ({q['category']}) {q['text']}")
        for j, fu in enumerate(q["follow_ups"], 1):
            print(f"    -> {fu}")
