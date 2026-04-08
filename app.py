import os
import json
import random
import re
import asyncio
import tempfile
import uuid
import time
import edge_tts
import requests as _requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyACq5_oEgRr7mJEJ2WnygE3Vvv2h-J-kjU")
GEMINI_MODEL = "gemini-2.0-flash-exp"
_GEMINI_CACHE = {}

def _gemini_call(prompt, max_tokens=200, temperature=0.8):
    """Lightweight Gemini REST call. Returns text or None on failure."""
    if not GEMINI_API_KEY:
        return None
    cache_key = (prompt[:200], max_tokens, temperature)
    if cache_key in _GEMINI_CACHE:
        return _GEMINI_CACHE[cache_key]
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        r = _requests.post(url, json=body, timeout=12)
        if r.status_code != 200:
            return None
        data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        _GEMINI_CACHE[cache_key] = text
        return text
    except Exception:
        return None


def gemini_generate_followup(prev_question, prev_answer, score, profile_summary):
    """Generate a hostile follow-up question using Gemini, referencing Ashish's profile."""
    prompt = f"""You are a SKEPTICAL, HOSTILE US visa officer cross-examining an Indian B1/B2 tourist visa applicant named Ashish Kumar.

Applicant profile (use these facts to corner him):
{profile_summary}

You just asked: "{prev_question}"
He answered: "{prev_answer}"
His answer scored {score}/100 (low = weak/evasive).

Generate ONE sharp, openly skeptical follow-up question that:
- References a specific fact from his profile
- Cross-examines the weak part of his answer
- Is 1-2 short sentences max
- No greetings, no "well", no fluff — just the question
- Sound like an annoyed officer who suspects he wants to overstay

Output ONLY the question text, nothing else."""
    return _gemini_call(prompt, max_tokens=80, temperature=0.9)


def gemini_score_answer(question, answer, profile_summary):
    """Use Gemini to score an answer 0-100 with one-sentence critique. Returns dict or None."""
    prompt = f"""You are a strict US visa officer scoring an Indian B1/B2 visa applicant's answer.

Profile:
{profile_summary}

Question: "{question}"
Answer: "{answer}"

Score this answer on 5 dimensions (0-10 each), and give a 1-sentence coach tip.
Return ONLY valid JSON in this exact format (no markdown, no extra text):
{{"clarity": 7, "confidence": 6, "specificity": 5, "relevance": 8, "honesty": 9, "tip": "your one sentence tip here"}}"""
    text = _gemini_call(prompt, max_tokens=150, temperature=0.3)
    if not text:
        return None
    try:
        text = text.strip().lstrip("`").rstrip("`")
        if text.startswith("json"):
            text = text[4:].strip()
        return json.loads(text)
    except Exception:
        return None


def _ashish_profile_summary():
    try:
        p = ASHISH_PROFILE
        return (
            f"Name: {p.get('full_name')}, Age {p.get('age')}, {p.get('occupation')} at {p.get('employer')} "
            f"in {p.get('city')}. Salary INR {p.get('salary_inr')}, savings INR {p.get('funds_inr')}. "
            f"Purpose: {p.get('purpose')}. Sponsor/host: {p.get('sponsor')} ({p.get('relation')}) in {p.get('host_city')}. "
            f"Trip: {p.get('trip_duration_days')} days, {p.get('trip_dates')}. Marital: {p.get('marital_status')}, "
            f"dependents: {p.get('dependents')}. Prior travel: {p.get('prior_travel')}."
        )
    except Exception:
        return "Ashish Kumar, Indian software engineer applying for B1/B2 tourist visa."


ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "sk_2adc5d2157b53c440b2cd0c94780fe377d75a8e92d8ab7bd")
# "Adam" — deep, mature American male, great for authority figures
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")

# D-ID — talking head video generation from a still photo
DID_API_KEY = os.environ.get("DID_API_KEY", "c2VucGFpZHJpcGJyYW5kQGdtYWlsLmNvbQ:eJqBK0-M5KWGVZ_kRroTO")
DID_SOURCE_URL = os.environ.get("DID_SOURCE_URL", "https://cdn.jsdelivr.net/gh/senpaidripbrand-web/visa-interview-simulator@main/static/officer.png")
DID_TALKS_CACHE = {}  # text -> result_url cache (in-memory)
import threading as _threading
import hashlib as _hashlib
TALKS_DIR = os.path.join(os.path.dirname(__file__), "audio_cache", "talks")
os.makedirs(TALKS_DIR, exist_ok=True)
_DID_LOCKS = {}  # per-text locks to avoid duplicate generation
_DID_LOCKS_LOCK = _threading.Lock()
from flask import Flask, render_template, request, jsonify, session, send_file
from coaching import get_instant_feedback, get_difficulty_settings
try:
    from ds160_parser import extract_profile, generate_personalized_questions
    DS160_AVAILABLE = True
except ImportError:
    DS160_AVAILABLE = False

app = Flask(__name__)
app.secret_key = "visa-interview-2026-fixed-key"  # FIXED key so sessions survive reloads

AUDIO_DIR = os.path.join(tempfile.gettempdir(), "visa_interview_audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

# Server-side session store
SESSIONS = {}

# ---------------------------------------------------------------------------
# Hardcoded Ashish profile (used for honesty/contradiction detection)
# NOTE: The existing question pool is FIFA/Ministry-themed and was kept intact
# (it already deeply references Ashish). This dict is the formal spec'd profile
# referenced by the rubric (honesty/contradictions) and shown in the UI chip.
# ---------------------------------------------------------------------------
ASHISH_PROFILE = {
    "full_name": "Ashish Kumar",
    "nationality": "Indian",
    "passport": "Z1234567",
    "dob": "1995-06-15",
    "visa_type": "B1/B2 Tourist",
    "purpose": "Tourism and visiting family",
    "duration": "14 days",
    "destination": "New York, Los Angeles, Las Vegas",
    "employer": "Infosys Limited, Bangalore",
    "position": "Senior Software Engineer",
    "salary_inr": "1,800,000 per year",
    "years_at_job": "4 years",
    "sponsor": "Self-funded",
    "funds_inr": "2,500,000 in savings",
    "ties_to_india": "Parents, sister, apartment in Bangalore, full-time job",
    "previous_us_travel": "Never visited US before",
    "previous_visa_refusals": "None",
    "family_in_us": "Cousin in New Jersey (US citizen)",
    "return_date": "Confirmed return ticket booked",
    "marital_status": "Single",
}

FILLER_WORDS = ["um", "uh", "like", "you know", "maybe", "i think", "i guess", "sort of", "kind of", "uhh", "umm"]

REJECTION_REASONS = {
    "intent_to_immigrate": {"code": "214(b)", "description": "Failure to overcome presumption of immigrant intent"},
    "contradiction": {"code": "Misrepresentation (6 C 1)", "description": "Statements inconsistent with DS-160 / profile"},
    "evasive": {"code": "214(b)", "description": "Insufficient credibility — evasive answers"},
    "weak_ties": {"code": "214(b)", "description": "Insufficient ties to home country"},
    "missing_info": {"code": "214(b)", "description": "Failure to articulate clear purpose"},
    "financial_inconsistency": {"code": "221(g)", "description": "Financial documentation inconsistent"},
}

# ---------------------------------------------------------------------------
# Ashish's REAL profile
# ---------------------------------------------------------------------------
# Job: Ministry of Communications, Central Govt, since 2020 (6 yrs)
# Salary: 12.5 lakh/year govt salary
# Married to Meenu, 5-month-old baby
# Travel: Turkey 2023, Saudi 2024 (Ronaldo-Messi), Germany/Hungary/Czech/Austria 2024 (Euro Cup),
#   Switzerland/Spain/Portugal/Italy 2025 (Real Madrid vs Barca)
# 1st refusal: Feb 2025 Hyderabad (with wife - wife couldn't answer)
# 2nd refusal: Dec 2025 Delhi (solo - officer suspicious about pregnant wife)
# NOW: FIFA WC June 2026:
#   Match 1: Portugal vs Congo — June 17, Houston
#   Match 2: France vs Iraq — June 22, Philadelphia
# ---------------------------------------------------------------------------

VOICE = "en-US-AndrewMultilingualNeural"

# --- ALL possible questions (pool of 20+) ---
ALL_QUESTIONS = [
    {
        "text": "What's the purpose of your visit to the United States?",
        "category": "purpose", "key": "purpose",
        "follow_ups": [
            "Which specific matches? Give me dates, cities, teams.",
            "Do you already have match tickets? Show me the confirmation.",
            "Group stage matches. You're spending all this money for group stage games?",
        ]
    },
    {
        "text": "I see two prior refusals on your file. Both 214(b). Tell me what happened.",
        "category": "ties", "key": "prior_refusals",
        "follow_ups": [
            "Two refusals in under a year. And now you're back again. What's changed?",
            "Why should I approve you when two officers already said no?",
        ]
    },
    {
        "text": "In your last interview, the officer noted you traveled to Europe while your wife was seven months pregnant. Explain that.",
        "category": "ties", "key": "pregnant_trip",
        "follow_ups": [
            "And you think that shows strong family ties? Leaving a pregnant wife?",
            "Was that Europe trip also for football?",
        ]
    },
    {
        "text": "What do you do for work?",
        "category": "ties", "key": "employment",
        "follow_ups": [
            "Central government or state? How long have you been there?",
            "Do you have approved leave for this trip?",
            "What happens to your government job if you overstay?",
        ]
    },
    {
        "text": "What's your annual income? How are you funding this trip?",
        "category": "financial", "key": "income",
        "follow_ups": [
            "Twelve and a half lakh. That's your total compensation? Break down the trip cost for me.",
            "Flights, hotels, tickets, spending money. How much total?",
        ]
    },
    {
        "text": "Walk me through your international travel history.",
        "category": "travel_history", "key": "travel",
        "follow_ups": [
            "That's a lot of countries. And you returned every single time?",
            "Were all of these trips for football?",
        ]
    },
    {
        "text": "You say you're a football fan. Prove it. What matches have you physically attended abroad?",
        "category": "purpose", "key": "football_proof",
        "follow_ups": [
            "Saudi Arabia for Ronaldo-Messi. Germany for Euro 2024. Spain for El Clasico. And now you want the World Cup.",
            "How much did you spend on the FIFA tickets?",
        ]
    },
    {
        "text": "You have a five-month-old baby at home. Who takes care of the baby while you're in the US?",
        "category": "ties", "key": "baby",
        "follow_ups": [
            "And your wife is okay with you leaving?",
            "A five-month-old is a strong reason to come back. But it's also a reason not to leave.",
        ]
    },
    {
        "text": "Is your wife applying with you this time?",
        "category": "ties", "key": "wife_applying",
        "follow_ups": [
            "Last time in Hyderabad she couldn't answer the officer's questions. What happened?",
            "Does your wife speak English?",
        ]
    },
    {
        "text": "The World Cup is broadcast live everywhere. Why do you need to physically be in the US?",
        "category": "purpose", "key": "why_us",
        "follow_ups": [
            "You've watched matches live in Saudi Arabia, Germany, Spain. Those countries didn't deny you twice. We did.",
            "One match in Houston, one in Philadelphia. What's your plan between the two?",
        ]
    },
    {
        "text": "What are your ties to India? What guarantees you're coming back?",
        "category": "ties", "key": "ties",
        "follow_ups": [
            "Give me something concrete. Property, obligations, anything binding.",
            "Government job, baby, wife, travel history. That's your whole argument?",
        ]
    },
    {
        "text": "Where exactly are you staying in the US? Walk me through your full itinerary.",
        "category": "purpose", "key": "accommodation",
        "follow_ups": [
            "Do you have hotel bookings for both cities?",
            "Five days between the two matches. What are you doing in that gap?",
        ]
    },
    {
        "text": "When are you returning to India? Do you have a return flight booked?",
        "category": "purpose", "key": "return",
        "follow_ups": [
            "Show me the booking confirmation.",
            "And then straight back to your government posting?",
        ]
    },
    {
        "text": "Do you have any family, friends, or contacts in the United States?",
        "category": "ties", "key": "family_us",
        "follow_ups": [
            "Nobody at all? No one from your community?",
            "Who is your emergency contact in Houston?",
        ]
    },
    {
        "text": "This is your third attempt. Two officers looked at your case and said no. Give me one reason why I should see this differently.",
        "category": "ties", "key": "final_pitch",
        "follow_ups": [
            "That's what everyone says. What new evidence do you have today that wasn't there before?",
            "What's different about your application this time?",
        ]
    },
    {
        "text": "Have you ever considered moving abroad permanently? Working or settling outside India?",
        "category": "ties", "key": "intent",
        "follow_ups": [
            "A government pension is hard to give up, isn't it?",
            "So you have zero intention of staying in the US?",
        ]
    },
    {
        "text": "How much money do you have in your bank account right now?",
        "category": "financial", "key": "bank_balance",
        "follow_ups": [
            "Show me the bank statement.",
            "Is that enough to cover the entire trip without any loans?",
        ]
    },
    {
        "text": "Who is sponsoring this trip? Are you paying for everything yourself?",
        "category": "financial", "key": "sponsor",
        "follow_ups": [
            "No financial support from anyone?",
            "How long did it take you to save for this?",
        ]
    },
    {
        "text": "You said you work for the Ministry of Communications. What exactly is your role there?",
        "category": "ties", "key": "role_detail",
        "follow_ups": [
            "And they're okay with you leaving for two weeks?",
            "Who handles your responsibilities while you're away?",
        ]
    },
    {
        "text": "Do you own any property in India? Land, house, anything in your name?",
        "category": "ties", "key": "property",
        "follow_ups": [
            "Whose name is it registered under?",
            "Can you show me the ownership documents?",
        ]
    },
    {
        "text": "Why Houston specifically? Is there something else you're planning to do there besides the match?",
        "category": "purpose", "key": "why_houston",
        "follow_ups": [
            "No sightseeing? No meetings? Just the match and back to the hotel?",
            "What about Philadelphia? Any other plans there?",
        ]
    },
    {
        "text": "How did you book the FIFA tickets? Through the official FIFA portal or a third party?",
        "category": "purpose", "key": "ticket_booking",
        "follow_ups": [
            "How much did each ticket cost?",
            "When did you buy them? Before or after the refusals?",
        ]
    },
]

OPENING = "Mr. Kumar. You work for Infosys in Bangalore making 18 lakhs a year. So why exactly should I let you spend 14 days in the United States?"

# Ideal answer templates for each question key (shown when user scores < 7)
IDEAL_ANSWERS = {
    "purpose": "I'm attending two FIFA World Cup 2026 matches on 14 days of approved leave — Portugal vs Congo June 17 in Houston, and France vs Iraq June 22 in Philadelphia. I have confirmed match tickets, return ticket, and self-funded the trip from my savings.",
    "prior_refusals": "Yes, two prior 214(b) refusals. February 2025 in Hyderabad my wife was nervous and couldn't answer. December 2025 in Delhi the officer had concerns about my Europe travel while my wife was pregnant. My situation is stronger now — I have a 5-month-old, 6 years at my job, and confirmed FIFA tickets.",
    "pregnant_trip": "The Europe trip was planned and booked before we knew about the pregnancy. My wife had full family support at home, her doctor cleared her, and I returned as always.",
    "employment": "Senior Software Engineer at Infosys Limited in Bangalore for 4 years. Permanent employee, approved leave letter in hand, and my manager is expecting me back on the 15th day.",
    "income": "18 lakhs per year at Infosys. Total trip budget is about 6 lakhs — flights, hotels, match tickets, and spending money. I have 25 lakhs in savings, paying for everything myself.",
    "travel": "Turkey 2023, Saudi Arabia 2024 for Ronaldo vs Messi, Germany, Hungary, Czech Republic, Austria 2024 for Euro Cup, and Switzerland, Spain, Portugal, Italy 2025 for El Clasico. I returned every single time on schedule.",
    "football_proof": "Saudi Arabia 2024 for Ronaldo-Messi, Germany 2024 for Euro Cup, Spain 2025 for El Clasico at the Bernabeu. I have stadium photos, ticket stubs, and passport stamps for all of them.",
    "baby": "My 5-month-old baby is home with my wife Meenu and her parents. She has full family support. The baby is the reason I'm definitely coming back on day 14.",
    "wife_applying": "No, solo this time. My wife is caring for our 5-month-old. Last Hyderabad interview she was nervous and couldn't answer — this time it's just me, prepared and direct.",
    "why_us": "The World Cup is only in the US in 2026. I've been to stadium matches in 4 continents — this is a once-in-a-lifetime chance to see it on American soil with the atmosphere I can only get in person.",
    "ties": "Permanent Infosys job 4 years, 18 lakhs salary, apartment in Bangalore, parents and sister in India, 5-month-old baby, wife, and 25 lakhs in savings. Return ticket confirmed.",
    "accommodation": "Marriott Houston June 16-19, then JetBlue to Philadelphia, Hilton Philadelphia June 20-23, then return flight June 24. Confirmation numbers in my folder.",
    "return": "Confirmed round-trip booking. Returning on day 14, straight back to Infosys on day 15. I have the booking reference here.",
    "family_us": "Just one cousin in New Jersey, US citizen. Not visiting him — I'm only in Houston and Philadelphia for the matches.",
    "final_pitch": "Three things are different: confirmed FIFA tickets I didn't have before, a 5-month-old baby that ties me to India, and a clean travel record across 10 countries where I returned every time.",
    "intent": "No. I have a permanent Infosys job, family, baby, and home in India. Zero interest in settling abroad — I've been to 10 countries and always come back.",
    "bank_balance": "25 lakhs in savings, statement from HDFC available. That's more than 4x the total trip cost.",
    "sponsor": "Self-funded entirely from my Infosys salary and savings. No sponsor, no loan.",
    "role_detail": "Senior Software Engineer at Infosys, Bangalore — 4 years, permanent, leading a 6-person team. Approved leave, manager expecting me back.",
    "property": "Apartment in Bangalore registered in my name, plus my family's ancestral property. Documents available.",
    "why_houston": "Houston is where my FIFA ticket is allocated — Portugal vs Congo June 17 at NRG Stadium. That's the only reason.",
    "ticket_booking": "Through the official FIFA ticketing portal, bought after the match draw. I have the booking confirmation emails with both match references.",
}

# Curveball hostile questions
CURVEBALLS = [
    "Why should I believe anything you've said?",
    "If I called your manager at Infosys right now, would they confirm this?",
    "What's the real reason you're going?",
    "Convince me you'll come back.",
]

# Officer reactions — SKEPTICAL HOSTILE PERSONA ONLY
GOOD_REACTIONS = [
    "Hmm.",
    "Is that so?",
    "Noted.",
    "We'll see.",
    "I'm listening.",
]
NEUTRAL_REACTIONS = [
    "Hmm.",
    "Is that so?",
    "I'm not convinced.",
    "Explain further.",
    "Go on.",
]
SKEPTICAL_REACTIONS = [
    "That doesn't quite add up.",
    "I'm not convinced.",
    "Hmm. Convenient.",
    "I've heard that before, Ashish.",
    "Look, be straight with me.",
    "See, that's the concern.",
    "Two other officers weren't convinced either.",
]
PROBE_REACTIONS = [
    "Too vague. Be specific.",
    "I need more than that.",
    "You've been through this twice. Be prepared.",
    "Names. Numbers. Dates.",
    "Come on, Ashish.",
]
CLOSING_LINES = [
    "Alright, I think I've heard enough. That'll be all, Ashish. You may step aside.",
    "Okay. That's all the questions I have. Thank you.",
    "I have what I need. You can step to the side.",
    "Alright, we're done here. Thank you for your time.",
]


def build_session_questions():
    """Build a fully randomized question set — different every single session."""
    # Reseed with high-entropy source each time
    random.seed(uuid.uuid4().int)

    # Must-ask: purpose + refusals (but even their position varies)
    must_keys = {"purpose", "prior_refusals"}
    must_ask = [q for q in ALL_QUESTIONS if q["key"] in must_keys]
    rest = [q for q in ALL_QUESTIONS if q["key"] not in must_keys]

    # Pick 6-8 random extras using sample (no repeats guaranteed)
    extra_count = random.randint(6, 8)
    extra = random.sample(rest, min(extra_count, len(rest)))

    # Combine and shuffle EVERYTHING — purpose might be 1st or 5th
    all_picked = must_ask + extra
    random.shuffle(all_picked)

    return all_picked


# Question-specific keywords — what a GOOD answer should contain for each question
QUESTION_KEYWORDS = {
    "purpose": ['fifa', 'world cup', 'match', 'football', 'soccer', 'houston', 'philadelphia',
                'portugal', 'congo', 'france', 'iraq', 'june', 'stadium', 'ticket', 'watch'],
    "prior_refusals": ['refused', 'denied', 'refusal', '214', 'wife', 'couldn', 'nervous',
                       'pregnant', 'changed', 'stronger', 'different', 'baby', 'first time', 'second time'],
    "pregnant_trip": ['planned', 'before', 'pregnancy', 'doctor', 'family support', 'healthy',
                      'came back', 'returned', 'euro', 'europe', 'scheduled'],
    "employment": ['ministry', 'communication', 'government', 'central', 'permanent', 'since 2020',
                   'six years', '6 years', 'posting', 'leave', 'approved'],
    "income": ['lakh', '12.5', 'twelve', 'salary', 'savings', 'bank', 'fund', 'pay', 'budget',
               'total cost', 'flight', 'hotel', 'afford'],
    "travel": ['turkey', 'saudi', 'germany', 'hungary', 'czech', 'austria', 'switzerland',
               'spain', 'portugal', 'italy', 'returned', 'came back', 'every time', 'countries'],
    "football_proof": ['saudi', 'ronaldo', 'messi', 'euro', 'el clasico', 'real madrid', 'barcelona',
                       'stadium', 'attended', 'watched', 'live', 'ticket'],
    "baby": ['wife', 'meenu', 'baby', 'child', 'infant', 'family', 'mother', 'parents',
             'take care', 'support', 'five month', '5 month'],
    "wife_applying": ['wife', 'meenu', 'together', 'alone', 'solo', 'nervous', 'english',
                      'hyderabad', 'first interview'],
    "why_us": ['experience', 'live', 'atmosphere', 'stadium', 'once in a lifetime', 'world cup',
               'dream', 'different', 'passion', 'fan'],
    "ties": ['government', 'job', 'permanent', 'wife', 'baby', 'property', 'pension', 'family',
             'return', 'obligation', 'posting', 'ministry'],
    "accommodation": ['hotel', 'booking', 'airbnb', 'stay', 'booked', 'confirmation', 'houston',
                      'philadelphia', 'itinerary', 'plan'],
    "return": ['return', 'flight', 'booked', 'ticket', 'date', 'back', 'round trip',
               'confirmed', 'booking', 'june', 'july'],
    "family_us": ['no one', 'nobody', 'no family', 'no friends', 'don\'t know anyone',
                  'no contacts', 'alone', 'hotel'],
    "final_pitch": ['changed', 'different', 'baby', 'stronger', 'ticket', 'proof', 'evidence',
                    'fifa', 'confirmed', 'travel history', 'returned'],
    "intent": ['no', 'never', 'india', 'permanent', 'pension', 'government', 'family',
               'settle', 'home', 'not interested', 'my country'],
    "bank_balance": ['lakh', 'savings', 'bank', 'statement', 'balance', 'amount',
                     'enough', 'sufficient', 'cover'],
    "sponsor": ['myself', 'self', 'own', 'savings', 'salary', 'no sponsor', 'paying',
                'fund', 'saved', 'my money'],
    "role_detail": ['ministry', 'communication', 'role', 'position', 'department', 'work',
                    'responsibility', 'officer', 'handle', 'manage'],
    "property": ['house', 'land', 'property', 'flat', 'apartment', 'own', 'registered',
                 'name', 'plot', 'agriculture', 'farm'],
    "why_houston": ['match', 'portugal', 'congo', 'stadium', 'nrg', 'venue', 'fifa',
                    'allocated', 'scheduled', 'that\'s where'],
    "ticket_booking": ['fifa', 'portal', 'official', 'website', 'lottery', 'bought', 'paid',
                       'confirmation', 'booked', 'online', 'app'],
}


def detect_red_flags(answer, question_key=None):
    """Return a list of red flag tags detected in the answer."""
    flags = []
    lower = answer.lower()

    immigrate_terms = ["stay there", "settle", "green card", "job in us", "job in the us",
                       "marry", "permanent residency", "find work in", "live in america", "live in the us"]
    if any(t in lower for t in immigrate_terms):
        flags.append("intent_to_immigrate")

    evasive_terms = ["don't know", "dont know", "not sure", "i'm not sure", "no idea", "can't remember"]
    if any(t in lower for t in evasive_terms):
        flags.append("evasive")

    # Contradictions with ASHISH_PROFILE.employer
    if re.search(r'\b(google|microsoft|amazon|tcs|wipro|tesla|meta|apple)\b', lower) and "infosys" not in lower:
        if question_key in ("employment", "role_detail", "income", None):
            flags.append("contradiction")

    if re.search(r"(no money|broke|can't afford|cant afford|no savings|empty account)", lower):
        flags.append("financial_inconsistency")

    if question_key == "purpose" and len(answer.split()) < 5:
        flags.append("missing_info")

    return flags


def count_filler_words(answer):
    lower = " " + answer.lower() + " "
    count = 0
    for fw in FILLER_WORDS:
        count += lower.count(" " + fw + " ")
    return count


def analyze_answer(answer, question_key=None):
    """Score an answer across multiple rubric dimensions.

    Returns a dict with: clarity, confidence, specificity, relevance, honesty,
    overall (0-100 weighted), red_flags, filler_words, inline_feedback.
    """
    lower = answer.lower()
    words = answer.split()
    wc = len(words)

    # Clarity
    if wc <= 1:
        clarity = 2
    elif wc < 4:
        clarity = 4
    elif wc < 8:
        clarity = 6
    elif wc < 25:
        clarity = 8
    elif wc < 50:
        clarity = 9
    else:
        clarity = 6

    # Confidence (filler-word inverse)
    fillers = count_filler_words(answer)
    if fillers == 0:
        confidence = 10
    elif fillers == 1:
        confidence = 8
    elif fillers == 2:
        confidence = 6
    elif fillers <= 4:
        confidence = 4
    else:
        confidence = 3
    confident_phrases = ['i have', 'i can show', 'confirmed', 'booked', 'i will return',
                         'absolutely', 'definitely', 'every time', 'always']
    if any(c in lower for c in confident_phrases):
        confidence = min(10, confidence + 1)

    # Specificity
    spec_score = 3
    if re.search(r'\d', answer):
        spec_score += 3
    if re.search(r'(lakh|crore|\$|rupee|usd|inr|dollars?)', lower):
        spec_score += 2
    if re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december|\d{1,2}/\d{1,2}|\d{4})', lower):
        spec_score += 2
    proper_nouns = len([w for w in words[1:] if w and w[0].isupper()])
    if proper_nouns >= 2:
        spec_score += 2
    specificity = min(10, spec_score)

    # Relevance
    if question_key and question_key in QUESTION_KEYWORDS:
        relevant_kw = QUESTION_KEYWORDS[question_key]
        hits = sum(1 for kw in relevant_kw if kw.lower() in lower)
        total = len(relevant_kw) or 1
        ratio = hits / total
        if ratio >= 0.4:
            relevance = 10
        elif ratio >= 0.25:
            relevance = 8
        elif ratio >= 0.1:
            relevance = 6
        elif hits > 0:
            relevance = 4
        else:
            relevance = 2
    else:
        relevance = 6

    # Honesty
    red_flags = detect_red_flags(answer, question_key)
    if "contradiction" in red_flags:
        honesty = 0
    elif "evasive" in red_flags:
        honesty = 5
    else:
        honesty = 9

    overall_10 = (clarity * 0.15 + confidence * 0.15 + specificity * 0.20 +
                  relevance * 0.25 + honesty * 0.25)
    overall_100 = round(overall_10 * 10)

    if "contradiction" in red_flags:
        tip = "That contradicts your DS-160 — stick to the truth."
    elif "evasive" in red_flags:
        tip = "Don't be evasive. Give a clear, direct answer."
    elif relevance <= 4:
        tip = "Off-topic — answer the actual question with specifics."
    elif specificity <= 4:
        tip = "Too vague — add concrete numbers, dates, or names."
    elif confidence <= 4:
        tip = f"{fillers} filler words detected. Speak with conviction."
    elif clarity <= 4:
        tip = "Too short — give a complete answer in 1-2 sentences."
    elif overall_100 >= 80:
        tip = "Strong answer. Keep that tone."
    else:
        tip = "Acceptable. Tighten it with one specific detail."

    return {
        "clarity": clarity,
        "confidence": confidence,
        "specificity": specificity,
        "relevance": relevance,
        "honesty": honesty,
        "overall": overall_100,
        "red_flags": red_flags,
        "filler_words": fillers,
        "inline_feedback": tip,
    }


def overall_score(answer, question_key=None):
    """Backward-compat helper that returns just the overall int score."""
    return analyze_answer(answer, question_key)["overall"]


def get_reaction(score):
    if score >= 70:
        return random.choice(GOOD_REACTIONS)
    elif score >= 50:
        return random.choice(NEUTRAL_REACTIONS)
    elif score >= 35:
        return random.choice(SKEPTICAL_REACTIONS)
    else:
        return random.choice(PROBE_REACTIONS)


def should_follow_up(score, answer, difficulty="medium"):
    # TODO: GEMINI_FOLLOWUP_HOOK — swap this heuristic for Gemini-generated follow-ups
    settings = get_difficulty_settings(difficulty)
    chance = settings["follow_up_chance"]
    # Aggressive: force follow-up if score < 60
    if score < 60:
        return True
    if len(answer.split()) < 8:
        return True
    if any(w in answer.lower() for w in ['maybe', 'i think', 'not sure', 'i guess']):
        return True
    return random.random() < chance


# ---------------------------------------------------------------------------
# Contradiction memory — extract facts from answers and detect conflicts
# ---------------------------------------------------------------------------
def extract_facts(answer):
    """Pull numbers/durations/places out of answer text."""
    facts = {"durations": [], "money": [], "places": [], "numbers": []}
    lower = answer.lower()
    # durations like "14 days" "21 days" "2 weeks"
    for m in re.finditer(r'(\d+)\s*(day|days|week|weeks|month|months|year|years)', lower):
        n = int(m.group(1))
        unit = m.group(2)
        if "week" in unit:
            n *= 7
            unit = "days"
        elif "month" in unit:
            n *= 30
            unit = "days"
        elif "year" in unit:
            n *= 365
            unit = "days"
        facts["durations"].append(n)
    # money "18 lakhs" "25 lakh"
    for m in re.finditer(r'(\d+(?:\.\d+)?)\s*(lakh|lakhs|crore|crores)', lower):
        facts["money"].append(float(m.group(1)))
    # known places
    for p in ["houston", "philadelphia", "new york", "los angeles", "las vegas", "bangalore",
              "delhi", "hyderabad", "mumbai", "infosys", "tcs", "wipro", "google", "ministry"]:
        if p in lower:
            facts["places"].append(p)
    return facts


def detect_contradictions(new_facts, stated):
    """Compare new facts against previously stated ones. Returns contradiction strings."""
    contradictions = []
    if new_facts["durations"] and stated.get("durations"):
        for d in new_facts["durations"]:
            for old in stated["durations"]:
                if old != d and abs(old - d) > 2:
                    contradictions.append(f"Earlier said {old} days, now {d} days")
                    break
    if new_facts["money"] and stated.get("money"):
        for m in new_facts["money"]:
            for old in stated["money"]:
                if old != m and abs(old - m) > 0.5:
                    contradictions.append(f"Earlier said {old} lakhs, now {m} lakhs")
                    break
    # Employer conflicts
    employer_conflicts = [("infosys", "ministry"), ("infosys", "google"), ("infosys", "tcs"),
                          ("infosys", "wipro")]
    for a, b in employer_conflicts:
        if a in new_facts["places"] and b in stated.get("places", []):
            contradictions.append(f"Earlier mentioned {b}, now saying {a}")
        elif b in new_facts["places"] and a in stated.get("places", []):
            contradictions.append(f"Earlier mentioned {a}, now saying {b}")
    return contradictions


def merge_facts(stated, new_facts):
    for k, v in new_facts.items():
        stated.setdefault(k, []).extend(v)
        # Dedupe
        stated[k] = list(dict.fromkeys(stated[k]))
    return stated


# ---------------------------------------------------------------------------
# Rate limiting (in-memory, 60 req/min/sid)
# ---------------------------------------------------------------------------
_RATE_BUCKETS = {}  # sid -> [timestamps]
_RATE_LIMIT = 60
_RATE_WINDOW = 60.0

def rate_limited(sid):
    now = time.time()
    bucket = _RATE_BUCKETS.setdefault(sid, [])
    # Drop old
    cutoff = now - _RATE_WINDOW
    bucket[:] = [t for t in bucket if t >= cutoff]
    if len(bucket) >= _RATE_LIMIT:
        return True
    bucket.append(now)
    return False


def generate_score_report(answers, visa_type):
    # Map of all possible category labels
    CAT_LABELS = {
        "purpose": "Purpose & Trip Clarity",
        "ties": "Ties to Home Country",
        "financial": "Financial Preparedness",
        "travel_history": "Travel History & Credibility",
    }

    # Only collect scores for categories that were ACTUALLY asked
    cat_scores_raw = {}   # key -> list of scores
    strengths = []
    weaknesses = []
    red_flags = ["Two prior 214(b) refusals — the burden of proof is significantly higher on your third attempt"]

    all_scores = []
    all_word_counts = []

    for ans in answers:
        score = ans["score"]
        text = ans["answer"]
        question = ans["question"]
        cat = ans.get("category", "purpose")
        wc = len(text.split())

        all_scores.append(score)
        all_word_counts.append(wc)

        # Only add to categories that were actually asked
        if cat not in cat_scores_raw:
            cat_scores_raw[cat] = []
        cat_scores_raw[cat].append(score)

        if score >= 70:
            strengths.append({"q": question, "a": text})
        elif score < 40:
            weaknesses.append({"q": question, "a": text})

        if any(w in text.lower() for w in ["don't know", "not sure", "maybe", "i guess"]):
            red_flags.append(f'Uncertain language on: "{question}"')
        if wc < 4:
            red_flags.append(f'Very brief answer to: "{question}"')

    # Build ONLY the categories that had real questions + 2 computed ones
    final_cats = {}

    # Confidence — computed from all answers (word count + score)
    conf_scores = [min(100, s + (15 if wc > 15 else (5 if wc > 8 else -10)))
                   for s, wc in zip(all_scores, all_word_counts)]
    if conf_scores:
        final_cats["confidence"] = {
            "label": "Confidence & Communication",
            "avg": sum(conf_scores) / len(conf_scores)
        }

    # Real question categories
    for cat_key, scores in cat_scores_raw.items():
        label = CAT_LABELS.get(cat_key, cat_key.replace("_", " ").title())
        final_cats[cat_key] = {
            "label": label,
            "avg": sum(scores) / len(scores)
        }

    # Consistency — how evenly you performed across all questions
    if len(all_scores) >= 2:
        avg_s = sum(all_scores) / len(all_scores)
        # Standard deviation (not variance) for a fairer scale
        std_dev = (sum((s - avg_s) ** 2 for s in all_scores) / len(all_scores)) ** 0.5
        # std_dev of 0 = perfect consistency (100), std_dev of 30+ = poor (40)
        consistency = max(40, min(95, 95 - std_dev * 1.5))
        # Bonus if most answers were decent
        if avg_s >= 60:
            consistency += 5
        final_cats["consistency"] = {
            "label": "Consistency & Coherence",
            "avg": min(95, consistency)
        }

    # Convert to /10 scale
    cat_display = {}
    for key, cat in final_cats.items():
        cat_display[key] = {
            "label": cat["label"],
            "score": round(min(10, max(1, cat["avg"] / 10)), 1)
        }

    # Overall from actual categories only
    if cat_display:
        overall = round(sum(c["score"] for c in cat_display.values()) / len(cat_display) * 10)
    else:
        overall = 30

    if overall >= 80:
        outcome = "APPROVED"
        outcome_note = "Excellent. You handled the pressure, addressed your refusal history, and demonstrated clear ties and purpose."
    elif overall >= 65:
        outcome = "LIKELY APPROVED"
        outcome_note = "Good interview. With two prior refusals the bar is very high. A few sharper answers would seal it."
    elif overall >= 50:
        outcome = "BORDERLINE"
        outcome_note = "Not strong enough for a third attempt. The officer would likely lean toward denial."
    elif overall >= 35:
        outcome = "LIKELY DENIED — 214(b)"
        outcome_note = "Multiple weak answers. With your refusal history, this would almost certainly be a third denial."
    else:
        outcome = "DENIED — 214(b)"
        outcome_note = "This interview would result in a third consecutive refusal. Critical preparation needed."

    report = f"## Overall Score: {overall}/100 — {outcome}\n\n"
    report += f"{outcome_note}\n\n---\n\n## Category Breakdown\n\n"

    for key, cat in cat_display.items():
        bar = "█" * int(cat["score"]) + "░" * (10 - int(cat["score"]))
        report += f"**{cat['label']}**: {cat['score']}/10 {bar}\n\n"

    report += "---\n\n"

    if strengths:
        report += "## What You Did Well\n\n"
        for s in strengths[:5]:
            short_a = s['a'][:100] + '...' if len(s['a']) > 100 else s['a']
            report += f'- **Q: "{s["q"]}"** — Strong answer: "{short_a}"\n\n'

    if weaknesses:
        report += "## Where You Fell Short\n\n"
        for w in weaknesses[:5]:
            short_a = w['a'][:100] + '...' if len(w['a']) > 100 else w['a']
            report += f'- **Q: "{w["q"]}"** — Weak answer: "{short_a}" — This leads to 214(b).\n\n'

    if red_flags:
        report += "## Red Flags\n\n"
        for rf in red_flags[:7]:
            report += f"- {rf}\n\n"

    report += "---\n\n## Your Game Plan for the Real Interview\n\n"
    report += "**Opening — Lead with FIFA immediately:**\n"
    report += "\"Officer, I'm here to attend two FIFA World Cup 2026 matches. Portugal versus Congo on June 17th in Houston, and France versus Iraq on June 22nd in Philadelphia. I already have both match tickets. I'm a lifelong football fan — I've traveled to Saudi Arabia, Germany, Spain, and other countries specifically to watch live matches.\"\n\n"
    report += "**On the refusals — Own it:**\n"
    report += "\"Yes, I was refused twice. The first time my wife was nervous and couldn't answer. The second time the officer had concerns about my travel while my wife was pregnant. Since then my situation has only gotten stronger — I now have a five-month-old baby, six years in my government position, and confirmed FIFA tickets.\"\n\n"
    report += "**On the pregnant wife trip:**\n"
    report += "\"The Europe trip was planned before we knew about the pregnancy. My wife had full family support at home. Doctors confirmed she was healthy. And I went and came back, as I always do.\"\n\n"
    report += "**On income — Be precise:**\n"
    report += "\"My government salary is twelve and a half lakh per annum. I can show you my bank statements and the total trip budget.\"\n\n"
    report += "**On ties — Stack them:**\n"
    report += "\"I'm a permanent Central Government employee with six years of service and a pension. My wife and five-month-old baby are in India. I've traveled to ten countries and returned every single time. Here is my approved leave letter from the Ministry.\"\n\n"

    return report


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def get_sid():
    sid = session.get("sid")
    if not sid or sid not in SESSIONS:
        sid = str(uuid.uuid4())
        session["sid"] = sid
        SESSIONS[sid] = {}
    return sid


@app.route("/")
def index():
    old_sid = session.get("sid")
    if old_sid and old_sid in SESSIONS:
        del SESSIONS[old_sid]
    session.clear()
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def start_interview():
    data = request.json or {}
    difficulty = "hard"  # Hostile officer — always

    sid = get_sid()
    if rate_limited(sid):
        return jsonify({"error": "rate_limited"}), 429

    # DS-160 upload removed — always use the hardcoded Ashish profile.
    questions = build_session_questions()
    applicant_name = "Ashish"

    diff_settings = get_difficulty_settings(difficulty)
    max_q = diff_settings["max_questions"]
    questions = questions[:max_q]

    SESSIONS[sid] = {
        **SESSIONS.get(sid, {}),
        "questions": questions,
        "current_q": 0,
        "answers": [],
        "pending_follow_up": None,
        "follow_up_used": 0,
        "got_opening_response": False,
        "start_time": time.time(),
        "asked_keys": set(),
        "last_asked_key": None,
        "follow_up_done_for": {},
        "difficulty": difficulty,
        "applicant_name": applicant_name,
        "profile": ASHISH_PROFILE,
        "total_fillers": 0,
        "patience": 100,
        "stated_facts": {},
        "forced_followup_remaining": 0,
        "last_parent_key": None,
    }

    return jsonify({
        "message": OPENING,
        "done": False,
        "difficulty": difficulty,
        "applicant": applicant_name,
        "profile": ASHISH_PROFILE,
    })


@app.route("/api/respond", methods=["POST"])
def respond():
    data = request.json
    user_message = data.get("message", "").strip()
    sid = get_sid()
    if rate_limited(sid):
        return jsonify({"error": "rate_limited"}), 429
    s = SESSIONS.get(sid, {})

    questions = s.get("questions", [])
    current_q = s.get("current_q", 0)
    answers = s.get("answers", [])
    pending_follow_up = s.get("pending_follow_up", None)
    follow_up_used = s.get("follow_up_used", 0)
    got_opening = s.get("got_opening_response", False)
    start_time = s.get("start_time", time.time())
    asked_keys = s.get("asked_keys", set())
    last_asked_key = s.get("last_asked_key", None)
    follow_up_done_for = s.get("follow_up_done_for", set())
    difficulty = s.get("difficulty", "medium")

    score = 50
    rubric = None
    stated_facts = s.get("stated_facts", {})
    patience = s.get("patience", 100)
    forced_fu_remaining = s.get("forced_followup_remaining", 0)
    last_parent_key = s.get("last_parent_key", None)
    contradictions_now = []

    # GEMINI_SCORING_HOOK — try Gemini rubric first, fall back to heuristic analyze_answer
    def _apply_gemini_rubric(rubric_obj, q_text):
        try:
            g = gemini_score_answer(q_text or "", user_message, _ashish_profile_summary())
            if not g:
                return rubric_obj
            for k in ("clarity", "confidence", "specificity", "relevance", "honesty"):
                if k in g and isinstance(g[k], (int, float)):
                    rubric_obj[k] = int(g[k])
            rubric_obj["overall"] = int(round(
                (rubric_obj["clarity"] + rubric_obj["confidence"] + rubric_obj["specificity"]
                 + rubric_obj["relevance"] + rubric_obj["honesty"]) * 2
            ))
            if g.get("tip"):
                rubric_obj["coach_tip"] = g["tip"]
            return rubric_obj
        except Exception:
            return rubric_obj

    if pending_follow_up:
        prev_idx = max(0, current_q - 1)
        parent_key = last_parent_key or (questions[prev_idx]["key"] if prev_idx < len(questions) else None)
        rubric = analyze_answer(user_message, question_key=parent_key)
        parent_q_text = next((qq["text"] for qq in questions if qq.get("key") == parent_key), "")
        rubric = _apply_gemini_rubric(rubric, parent_q_text)
        score = rubric["overall"]
        new_facts = extract_facts(user_message)
        contradictions_now = detect_contradictions(new_facts, stated_facts)
        if contradictions_now:
            rubric["red_flags"].append("contradiction")
            score = max(10, score - 20)
        merge_facts(stated_facts, new_facts)
        if answers:
            answers[-1]["follow_up_answer"] = user_message
            answers[-1]["score"] = (answers[-1]["score"] + score) // 2
            answers[-1].setdefault("red_flags", []).extend(rubric["red_flags"])
        pending_follow_up = None
    elif got_opening:
        if current_q < len(questions):
            q = questions[current_q]
            rubric = analyze_answer(user_message, question_key=q["key"])
            rubric = _apply_gemini_rubric(rubric, q["text"])
            score = rubric["overall"]
            new_facts = extract_facts(user_message)
            contradictions_now = detect_contradictions(new_facts, stated_facts)
            if contradictions_now:
                rubric["red_flags"].append("contradiction")
                score = max(10, score - 20)
            merge_facts(stated_facts, new_facts)
            answers.append({
                "question": q["text"],
                "answer": user_message,
                "score": score,
                "category": q.get("category", "purpose"),
                "key": q["key"],
                "rubric": {k: rubric[k] for k in ("clarity", "confidence", "specificity", "relevance", "honesty")},
                "red_flags": list(rubric["red_flags"]),
                "filler_words": rubric["filler_words"],
                "contradictions": list(contradictions_now),
            })
            asked_keys.add(q["key"])
            last_parent_key = q["key"]
        else:
            rubric = analyze_answer(user_message)
            score = rubric["overall"]
        current_q += 1

    # Update patience meter
    patience += (score - 50) / 8.0
    patience = max(0, min(100, patience))

    # --- Helper: find next un-asked question (skip duplicates) ---
    def find_next_q(start_idx):
        idx = start_idx
        while idx < len(questions):
            qkey = questions[idx]["key"]
            if qkey not in asked_keys:
                return idx
            idx += 1
        return None

    # --- Decide next action ---
    elapsed = time.time() - start_time
    max_time = 300  # 5 minutes

    done = False
    officer_msg = ""

    if got_opening and patience <= 0:
        officer_msg = "That's enough. I've heard plenty. Your application is refused under 214(b). Step aside."
        done = True
    elif not got_opening:
        got_opening = True
        # The OPENING itself counts as the first real question (purpose).
        rubric = analyze_answer(user_message, question_key="purpose")
        score = rubric["overall"]
        new_facts = extract_facts(user_message)
        merge_facts(stated_facts, new_facts)
        answers.append({
            "question": OPENING,
            "answer": user_message,
            "score": score,
            "category": "purpose",
            "key": "purpose",
            "rubric": {k: rubric[k] for k in ("clarity", "confidence", "specificity", "relevance", "honesty")},
            "red_flags": list(rubric["red_flags"]),
            "filler_words": rubric["filler_words"],
            "contradictions": [],
        })
        asked_keys.add("purpose")
        patience += (score - 50) / 8.0
        patience = max(0, min(100, patience))
        last_parent_key = "purpose"

        next_idx = find_next_q(0)
        if next_idx is not None:
            reaction = get_reaction(score)
            officer_msg = f"{reaction} {questions[next_idx]['text']}"
            current_q = next_idx + 1
            last_asked_key = questions[next_idx]["key"]
            asked_keys.add(questions[next_idx]["key"])
            last_parent_key = questions[next_idx]["key"]
        else:
            officer_msg = random.choice(CLOSING_LINES)
            done = True
    else:
        prev_key = last_parent_key
        prev_q = None
        for qq in questions:
            if qq.get("key") == prev_key:
                prev_q = qq
                break
        follow_ups = prev_q.get("follow_ups", []) if prev_q else []
        fu_count_done = follow_up_done_for.get(prev_key, 0) if prev_key else 0

        if score < 60 and prev_key and fu_count_done < 2 and follow_ups:
            forced_fu_remaining = max(forced_fu_remaining, 2 - fu_count_done)

        prefix = ""
        if contradictions_now:
            prefix = f"Hold on. {contradictions_now[0]}. "

        if forced_fu_remaining > 0 and follow_ups and fu_count_done < len(follow_ups):
            reaction = get_reaction(score)
            fu = follow_ups[fu_count_done % len(follow_ups)]
            try:
                prev_q_text = (prev_q or {}).get("text", "")
                g_fu = gemini_generate_followup(prev_q_text, user_message, score, _ashish_profile_summary())
                if g_fu:
                    fu = g_fu.strip().strip('"').strip()
            except Exception:
                pass
            officer_msg = f"{prefix}{reaction} {fu}"
            pending_follow_up = fu
            follow_up_done_for[prev_key] = fu_count_done + 1
            forced_fu_remaining -= 1
        elif pending_follow_up is None and prev_key and should_follow_up(score, user_message, difficulty) \
                and follow_ups and fu_count_done < 1:
            reaction = get_reaction(score)
            fu = random.choice(follow_ups)
            try:
                prev_q_text = (prev_q or {}).get("text", "")
                g_fu = gemini_generate_followup(prev_q_text, user_message, score, _ashish_profile_summary())
                if g_fu:
                    fu = g_fu.strip().strip('"').strip()
            except Exception:
                pass
            officer_msg = f"{prefix}{reaction} {fu}"
            pending_follow_up = fu
            follow_up_done_for[prev_key] = fu_count_done + 1
        else:
            if random.random() < 0.2 and elapsed < max_time - 30:
                cb = random.choice(CURVEBALLS)
                reaction = get_reaction(score)
                officer_msg = f"{prefix}{reaction} {cb}"
                cb_key = f"curveball_{uuid.uuid4().hex[:6]}"
                questions.append({"text": cb, "key": cb_key, "category": "purpose", "follow_ups": []})
                asked_keys.add(cb_key)
                last_asked_key = cb_key
                last_parent_key = cb_key
                current_q = len(questions)
            else:
                next_idx = find_next_q(current_q)
                if next_idx is not None and elapsed < max_time:
                    reaction = get_reaction(score)
                    officer_msg = f"{prefix}{reaction} {questions[next_idx]['text']}"
                    current_q = next_idx + 1
                    last_asked_key = questions[next_idx]["key"]
                    asked_keys.add(questions[next_idx]["key"])
                    last_parent_key = questions[next_idx]["key"]
                else:
                    officer_msg = random.choice(CLOSING_LINES)
                    done = True

    # Save state
    s["current_q"] = current_q
    s["answers"] = answers
    s["questions"] = questions
    s["pending_follow_up"] = pending_follow_up
    s["follow_up_used"] = follow_up_used
    s["got_opening_response"] = got_opening
    s["asked_keys"] = asked_keys
    s["last_asked_key"] = last_asked_key
    s["follow_up_done_for"] = follow_up_done_for
    s["stated_facts"] = stated_facts
    s["patience"] = patience
    s["forced_followup_remaining"] = forced_fu_remaining
    s["last_parent_key"] = last_parent_key

    coaching = None
    if got_opening and user_message and current_q > 0:
        prev_idx = max(0, current_q - 1)
        if prev_idx < len(questions):
            q_key = questions[prev_idx]["key"]
            try:
                coaching = get_instant_feedback(user_message, q_key, score)
            except Exception:
                coaching = None

    inline_coaching = None
    if rubric is not None:
        ideal = None
        if score < 70 and last_parent_key:
            ideal = IDEAL_ANSWERS.get(last_parent_key)
        inline_coaching = {
            "last_answer_score": round(rubric["overall"] / 10, 1),
            "tip": rubric["inline_feedback"],
            "red_flags": rubric["red_flags"],
            "contradictions": contradictions_now,
            "ideal_answer": ideal,
            "rubric": {
                "clarity": rubric["clarity"],
                "confidence": rubric["confidence"],
                "specificity": rubric["specificity"],
                "relevance": rubric["relevance"],
                "honesty": rubric["honesty"],
            },
        }

    s["total_fillers"] = s.get("total_fillers", 0) + (rubric["filler_words"] if rubric else 0)

    if done:
        try:
            save_transcript_to_disk(s)
        except Exception as _e:
            print(f"[transcript save failed] {_e}")

    return jsonify({
        "message": officer_msg,
        "done": done,
        "coaching": coaching,
        "inline_coaching": inline_coaching,
        "total_fillers": s["total_fillers"],
        "score": score,
        "patience": round(patience),
    })


async def _generate_speech(text, mp3_path):
    communicate = edge_tts.Communicate(text, VOICE, rate="-8%", pitch="-3Hz")
    await communicate.save(mp3_path)


def _generate_speech_elevenlabs(text, mp3_path):
    """Try ElevenLabs first; raises on failure so caller can fall back."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.85,
            "style": 0.55,
            "use_speaker_boost": True,
        },
    }
    r = _requests.post(url, json=payload, headers=headers, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:200]}")
    with open(mp3_path, "wb") as f:
        f.write(r.content)


def _elevenlabs_with_timestamps(text):
    """Returns (audio_b64, words, wtimes_ms, wdurations_ms) or raises."""
    import base64 as _b64
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/with-timestamps"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "output_format": "mp3_44100_128",
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.85,
            "style": 0.55,
            "use_speaker_boost": True,
        },
    }
    r = _requests.post(url, json=payload, headers=headers, timeout=40)
    if r.status_code != 200:
        raise RuntimeError(f"EL/ts {r.status_code}: {r.text[:200]}")
    j = r.json()
    audio_b64 = j["audio_base64"]
    align = j.get("alignment") or j.get("normalized_alignment") or {}
    chars = align.get("characters", [])
    starts = align.get("character_start_times_seconds", [])
    ends = align.get("character_end_times_seconds", [])

    words, wtimes, wdurations = [], [], []
    cur, cur_start, cur_end = "", None, None
    for ch, st, en in zip(chars, starts, ends):
        if ch.isspace() or ch in ".,!?;:\"'()[]":
            if cur:
                words.append(cur)
                wtimes.append(int((cur_start or 0) * 1000))
                wdurations.append(max(80, int(((cur_end or cur_start or 0) - (cur_start or 0)) * 1000)))
                cur, cur_start, cur_end = "", None, None
        else:
            if cur_start is None:
                cur_start = st
            cur_end = en
            cur += ch
    if cur:
        words.append(cur)
        wtimes.append(int((cur_start or 0) * 1000))
        wdurations.append(max(80, int(((cur_end or cur_start or 0) - (cur_start or 0)) * 1000)))

    return audio_b64, words, wtimes, wdurations


DID_DISABLED = True  # D-ID free credits exhausted — using SadTalker on Colab instead

# --- SadTalker (Colab + ngrok) config ---
SADTALKER_URL = os.environ.get("SADTALKER_URL", "")  # disabled — static photo + ElevenLabs voice instead
SADTALKER_SECRET = os.environ.get("SADTALKER_SECRET", "visa-officer-secret-2026")

def _sadtalker_create_talk(text):
    if not SADTALKER_URL:
        raise RuntimeError("SadTalker disabled")
    """Call Colab SadTalker server, save mp4 to disk, return local URL."""
    key = _hashlib.md5(text.encode("utf-8")).hexdigest()
    fname = f"{key}.mp4"
    fpath = os.path.join(TALKS_DIR, fname)
    if os.path.exists(fpath) and os.path.getsize(fpath) > 1000:
        return f"/api/talk_video/{fname}"

    with _DID_LOCKS_LOCK:
        lock = _DID_LOCKS.setdefault(key, _threading.Lock())
    with lock:
        if os.path.exists(fpath) and os.path.getsize(fpath) > 1000:
            return f"/api/talk_video/{fname}"
        r = _requests.post(
            f"{SADTALKER_URL.rstrip('/')}/talk",
            json={"text": text},
            headers={"X-Secret": SADTALKER_SECRET, "ngrok-skip-browser-warning": "true"},
            timeout=300,
            stream=True,
        )
        if r.status_code != 200:
            raise RuntimeError(f"SadTalker {r.status_code}: {r.text[:300]}")
        with open(fpath, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
        return f"/api/talk_video/{fname}"


@app.route("/api/talk_video/<filename>")
def talk_video(filename):
    filename = os.path.basename(filename)
    path = os.path.join(TALKS_DIR, filename)
    if not os.path.exists(path):
        return "", 404
    return send_file(path, mimetype="video/mp4")


def _did_create_talk(text):
    """Legacy D-ID function — now routes to SadTalker."""
    return _sadtalker_create_talk(text)

def _did_create_talk_OLD(text):
    if DID_DISABLED:
        raise RuntimeError("D-ID disabled (credits exhausted)")
    if text in DID_TALKS_CACHE:
        return DID_TALKS_CACHE[text]

    headers = {
        "Authorization": f"Basic {DID_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "source_url": DID_SOURCE_URL,
        "script": {
            "type": "text",
            "input": text,
            "provider": {
                "type": "microsoft",
                "voice_id": "en-US-DavisNeural",
                "voice_config": {"style": "Default"},
            },
        },
        "config": {
            "fluent": True,
            "pad_audio": 0.0,
            "stitch": True,
            "result_format": "mp4",
        },
    }
    r = _requests.post("https://api.d-id.com/talks", json=payload, headers=headers, timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"D-ID create {r.status_code}: {r.text[:300]}")
    talk_id = r.json()["id"]

    # Poll for completion
    import time as _time
    for _ in range(40):  # up to ~40s
        _time.sleep(1)
        pr = _requests.get(f"https://api.d-id.com/talks/{talk_id}", headers=headers, timeout=15)
        if pr.status_code != 200:
            continue
        pj = pr.json()
        status = pj.get("status")
        if status == "done":
            url = pj.get("result_url")
            if url:
                DID_TALKS_CACHE[text] = url
                return url
        if status in ("error", "rejected"):
            raise RuntimeError(f"D-ID failed: {pj}")
    raise RuntimeError("D-ID timed out")


@app.route("/api/talk", methods=["POST"])
def talk():
    data = request.json or {}
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No text"}), 400
    try:
        video_url = _did_create_talk(text)
        return jsonify({"video_url": video_url})
    except Exception as e:
        print(f"[D-ID failed] {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/speak", methods=["POST"])
def speak():
    data = request.json
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No text"}), 400

    # Path 0: D-ID talking-head video (real lip-sync on the officer photo)
    try:
        video_url = _did_create_talk(text)
        return jsonify({"video_url": video_url})
    except Exception as did_err:
        print(f"[D-ID failed -> audio fallback] {did_err}")

    # Path A: ElevenLabs with character timestamps (for 3D lip-sync)
    try:
        audio_b64, words, wtimes, wdurations = _elevenlabs_with_timestamps(text)
        return jsonify({
            "audio_b64": audio_b64,
            "words": words,
            "wtimes": wtimes,
            "wdurations": wdurations,
        })
    except Exception as el_err:
        print(f"[EL timestamps failed -> file fallback] {el_err}")

    # Path B: file-based fallback (ElevenLabs plain or Edge TTS)
    audio_id = str(uuid.uuid4())
    mp3_path = os.path.join(AUDIO_DIR, f"{audio_id}.mp3")
    try:
        _generate_speech_elevenlabs(text, mp3_path)
    except Exception as el2:
        print(f"[EL plain failed -> Edge TTS] {el2}")
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_generate_speech(text, mp3_path))
            loop.close()
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"audio_id": audio_id})


@app.route("/api/audio/<audio_id>")
def get_audio(audio_id):
    audio_id = os.path.basename(audio_id)
    mp3_path = os.path.join(AUDIO_DIR, f"{audio_id}.mp3")
    if not os.path.exists(mp3_path):
        return jsonify({"error": "Not found"}), 404
    response = send_file(mp3_path, mimetype="audio/mpeg")
    @response.call_on_close
    def cleanup():
        try:
            os.remove(mp3_path)
        except OSError:
            pass
    return response


def build_rubric_report(answers):
    """Build the rubric/red-flag/rejection-reason report dict."""
    dims = ["clarity", "confidence", "specificity", "relevance", "honesty"]
    sums = {d: 0.0 for d in dims}
    n = 0
    all_red_flags = []
    rejection_reasons = []
    seen_reasons = set()
    strengths = []
    weaknesses = []

    for i, ans in enumerate(answers, 1):
        rub = ans.get("rubric") or {}
        if rub:
            for d in dims:
                sums[d] += rub.get(d, 0)
            n += 1
        for rf in ans.get("red_flags", []):
            all_red_flags.append({"flag": rf, "answer_index": i, "question": ans.get("question", "")})
            if rf not in seen_reasons and rf in REJECTION_REASONS:
                seen_reasons.add(rf)
                rejection_reasons.append({
                    "code": REJECTION_REASONS[rf]["code"],
                    "description": REJECTION_REASONS[rf]["description"],
                    "triggered_by": f"answer #{i}",
                })
        sc = ans.get("score", 0)
        if sc >= 70:
            strengths.append(ans.get("question", ""))
        elif sc < 40:
            weaknesses.append(ans.get("question", ""))

    rubric_avg = {d: round(sums[d] / n, 1) if n else 0 for d in dims}
    overall = 0
    if n:
        overall = round((rubric_avg["clarity"] * 0.15 + rubric_avg["confidence"] * 0.15 +
                         rubric_avg["specificity"] * 0.20 + rubric_avg["relevance"] * 0.25 +
                         rubric_avg["honesty"] * 0.25) * 10)

    if overall >= 75:
        verdict = "LIKELY APPROVAL"
    elif overall >= 55:
        verdict = "BORDERLINE"
    else:
        verdict = "LIKELY DENIAL"

    weak_str = "; ".join(d for d, v in rubric_avg.items() if v < 6) or "none"
    coach_summary = (
        f"Overall {overall}/100 — {verdict}. Weak dimensions: {weak_str}. "
        f"{len(all_red_flags)} red flag(s) detected."
    )

    return {
        "overall_score": overall,
        "verdict": verdict,
        "rubric_avg": rubric_avg,
        "red_flags_summary": all_red_flags,
        "rejection_reasons": rejection_reasons,
        "strengths": strengths[:5],
        "weaknesses": weaknesses[:5],
        "coach_summary": coach_summary,
    }


TRANSCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "audio_cache", "transcripts")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)


def build_full_score(answers, s):
    report = build_rubric_report(answers)
    overall = report["overall_score"]
    if overall >= 75:
        verdict = "LIKELY APPROVAL"
        verdict_color = "#4caf50"
    elif overall >= 55:
        verdict = "BORDERLINE"
        verdict_color = "#ff9800"
    else:
        verdict = "LIKELY DENIAL"
        verdict_color = "#ef4444"

    dims = ["clarity", "confidence", "specificity", "relevance", "honesty"]
    rubric_avg = report["rubric_avg"]
    weakest = min(dims, key=lambda d: rubric_avg.get(d, 10)) if rubric_avg else "specificity"

    strengths = []
    weaknesses = []
    for a in answers:
        sc = a.get("score", 0)
        if sc >= 70 and len(strengths) < 3:
            strengths.append(f"{a.get('question', '')[:60]} — strong answer")
        elif sc < 45 and len(weaknesses) < 3:
            weaknesses.append(f"{a.get('question', '')[:60]} — needs detail")
    while len(strengths) < 3:
        strengths.append("Showed up prepared")
    while len(weaknesses) < 3:
        weaknesses.append(f"Weakest dimension: {weakest}")

    red_flags_summary = [
        {"flag": rf["flag"], "question": rf.get("question", "")}
        for rf in report.get("red_flags_summary", [])
    ]

    transcript = []
    for a in answers:
        transcript.append({
            "q": a.get("question", ""),
            "a": a.get("answer", ""),
            "score": round(a.get("score", 0) / 10, 1),
            "rubric": a.get("rubric", {}),
            "red_flags": a.get("red_flags", []),
            "contradictions": a.get("contradictions", []),
        })

    feedback_md = generate_score_report(answers, "B1/B2")
    return {
        "feedback": feedback_md,
        "overall_score": overall,
        "verdict": verdict,
        "verdict_color": verdict_color,
        "rubric_avg": rubric_avg,
        "red_flags_summary": red_flags_summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "coach_summary": report.get("coach_summary", ""),
        "transcript": transcript,
        "weakest_dimension": weakest,
        "total_fillers": s.get("total_fillers", 0),
        "report": report,  # back-compat
    }


def save_transcript_to_disk(s):
    answers = s.get("answers", [])
    if not answers:
        return
    payload = build_full_score(answers, s)
    ts = int(time.time())
    path = os.path.join(TRANSCRIPTS_DIR, f"{ts}.json")
    with open(path, "w") as f:
        json.dump({
            "timestamp": ts,
            "date": time.strftime("%Y-%m-%d %H:%M", time.localtime(ts)),
            "overall_score": payload["overall_score"],
            "verdict": payload["verdict"],
            "transcript": payload["transcript"],
        }, f)


@app.route("/api/past_interviews", methods=["GET"])
def past_interviews():
    out = []
    try:
        files = sorted(os.listdir(TRANSCRIPTS_DIR), reverse=True)[:50]
        for fname in files:
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(TRANSCRIPTS_DIR, fname)) as f:
                    data = json.load(f)
                out.append({
                    "id": fname.replace(".json", ""),
                    "date": data.get("date"),
                    "score": data.get("overall_score"),
                    "verdict": data.get("verdict"),
                    "transcript": data.get("transcript", []),
                })
            except Exception:
                continue
    except Exception:
        pass
    return jsonify({"past": out})


@app.route("/api/score", methods=["POST"])
def score():
    sid = get_sid()
    if rate_limited(sid):
        return jsonify({"error": "rate_limited"}), 429
    s = SESSIONS.get(sid, {})
    answers = s.get("answers", [])

    if not answers:
        return jsonify({"feedback": "No answers were recorded. Please try the interview again."})

    try:
        save_transcript_to_disk(s)
    except Exception as _e:
        print(f"[transcript save failed] {_e}")

    return jsonify(build_full_score(answers, s))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, host="0.0.0.0", port=port)
