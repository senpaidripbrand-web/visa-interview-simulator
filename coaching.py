"""Real-time coaching engine — gives instant feedback after each answer."""

# What makes a STRONG answer for each question key
ANSWER_CRITERIA = {
    "purpose": {
        "must_have": ["specific event/reason", "dates", "city/location"],
        "good_keywords": ["fifa", "world cup", "match", "conference", "business", "meeting",
                          "june", "july", "houston", "philadelphia", "ticket", "booked",
                          "attend", "visit", "tourism", "wedding", "graduation"],
        "tips": {
            "weak": "Be specific! Name exact dates, cities, and what you'll be doing.",
            "okay": "Good start. Add more detail — exact dates and proof of plans (tickets, bookings).",
            "strong": None
        }
    },
    "prior_refusals": {
        "must_have": ["acknowledge refusal", "explain what changed", "own it"],
        "good_keywords": ["refused", "denied", "changed", "stronger", "different", "first time",
                          "second time", "wife", "nervous", "baby", "now", "since then",
                          "improved", "more evidence", "proof"],
        "tips": {
            "weak": "Never dodge refusal history. Own it, explain what happened, and show what's CHANGED since.",
            "okay": "You acknowledged it. Now emphasize what's DIFFERENT this time — new evidence, stronger ties.",
            "strong": None
        }
    },
    "pregnant_trip": {
        "must_have": ["explanation", "family support", "returned"],
        "good_keywords": ["planned", "before", "pregnancy", "doctor", "family", "support",
                          "healthy", "returned", "came back", "scheduled", "euro"],
        "tips": {
            "weak": "Explain the timing — was the trip planned before the pregnancy? Did doctors clear it?",
            "okay": "Good. Emphasize that family was there for support AND you came back as planned.",
            "strong": None
        }
    },
    "employment": {
        "must_have": ["job title", "employer name", "duration"],
        "good_keywords": ["ministry", "government", "permanent", "years", "since", "posted",
                          "leave", "approved", "central", "officer", "manager", "engineer",
                          "company", "work", "employed"],
        "tips": {
            "weak": "State clearly: employer name, your role, how long, and that you have approved leave.",
            "okay": "Mention how long you've been there and whether you have a leave letter.",
            "strong": None
        }
    },
    "income": {
        "must_have": ["exact number", "currency", "how paying"],
        "good_keywords": ["lakh", "12.5", "salary", "savings", "bank", "statement", "fund",
                          "budget", "afford", "paying myself", "crore", "income", "per annum",
                          "monthly", "annually"],
        "tips": {
            "weak": "ALWAYS give exact figures. '12.5 lakh per annum' not 'good salary'. Break down trip cost.",
            "okay": "You gave a number. Now break down the trip cost: flights, hotels, tickets, spending.",
            "strong": None
        }
    },
    "travel": {
        "must_have": ["countries visited", "returned each time"],
        "good_keywords": ["turkey", "saudi", "germany", "hungary", "czech", "austria",
                          "switzerland", "spain", "portugal", "italy", "returned", "came back",
                          "every time", "countries", "traveled", "visited", "schengen"],
        "tips": {
            "weak": "List specific countries and dates. Emphasize: 'I returned every single time.'",
            "okay": "Good list. Make sure to emphasize the pattern: traveled widely, always came back.",
            "strong": None
        }
    },
    "football_proof": {
        "must_have": ["specific matches attended", "proof"],
        "good_keywords": ["saudi", "ronaldo", "messi", "euro", "el clasico", "real madrid",
                          "barcelona", "stadium", "attended", "watched", "live", "ticket"],
        "tips": {
            "weak": "Name specific matches: 'Ronaldo vs Messi in Saudi Arabia 2024, Euro Cup in Germany 2024'",
            "okay": "Good examples. Mention how much you spent on tickets to show commitment.",
            "strong": None
        }
    },
    "baby": {
        "must_have": ["baby exists", "who cares for baby", "reason to return"],
        "good_keywords": ["wife", "baby", "child", "infant", "family", "mother", "parents",
                          "take care", "support", "five month", "5 month", "home"],
        "tips": {
            "weak": "Mention your baby's age, that your wife is caring for them, and that they're your reason to return.",
            "okay": "Good. Emphasize the emotional tie — this is your strongest reason to come back.",
            "strong": None
        }
    },
    "wife_applying": {
        "must_have": ["clear answer", "explanation"],
        "good_keywords": ["wife", "together", "alone", "solo", "nervous", "english",
                          "baby", "staying", "home"],
        "tips": {
            "weak": "Be direct. If she's coming, explain why. If not, explain why not (baby, work, etc).",
            "okay": "Clear answer. If she's not coming, emphasize the baby needs her at home.",
            "strong": None
        }
    },
    "why_us": {
        "must_have": ["specific reason", "passion/purpose"],
        "good_keywords": ["experience", "live", "atmosphere", "stadium", "once in a lifetime",
                          "world cup", "dream", "passion", "fan", "football", "bucket list"],
        "tips": {
            "weak": "Explain your passion. 'Watching the FIFA World Cup live is a lifelong dream. I've traveled to 10 countries for football.'",
            "okay": "Good reasoning. Connect it to your travel pattern — you always go for football and return.",
            "strong": None
        }
    },
    "ties": {
        "must_have": ["multiple ties stacked"],
        "good_keywords": ["government", "job", "permanent", "wife", "baby", "property",
                          "pension", "family", "return", "obligation", "ministry", "land"],
        "tips": {
            "weak": "Stack your ties: 'Government job with pension + wife and baby + property + 6 years of service'",
            "okay": "Good. Stack MORE ties in one answer — job, family, property, pension, travel history.",
            "strong": None
        }
    },
    "accommodation": {
        "must_have": ["hotel/stay details", "city"],
        "good_keywords": ["hotel", "booking", "airbnb", "stay", "booked", "confirmation",
                          "houston", "philadelphia", "itinerary", "plan", "reservation"],
        "tips": {
            "weak": "Name the hotel, the city, and show a booking confirmation.",
            "okay": "Good. Mention the full itinerary: arrive date, hotel, match, travel, depart date.",
            "strong": None
        }
    },
    "return": {
        "must_have": ["return date", "booked ticket"],
        "good_keywords": ["return", "flight", "booked", "ticket", "date", "back", "round trip",
                          "confirmed", "booking", "june", "july", "departure"],
        "tips": {
            "weak": "Always have a return flight booked. Say the exact date: 'My return flight is on June 24th.'",
            "okay": "You mentioned returning. Confirm you have the booking and can show proof.",
            "strong": None
        }
    },
    "family_us": {
        "must_have": ["clear yes/no"],
        "good_keywords": ["no one", "nobody", "no family", "no friends", "don't know anyone",
                          "no contacts", "alone", "hotel", "yes", "relative", "friend"],
        "tips": {
            "weak": "Be direct — 'No, I don't know anyone in the US' is fine. Don't be vague.",
            "okay": "Good. If you said no, that actually helps — your life is entirely in your home country.",
            "strong": None
        }
    },
    "final_pitch": {
        "must_have": ["concrete reason", "evidence"],
        "good_keywords": ["changed", "different", "baby", "stronger", "ticket", "proof",
                          "evidence", "fifa", "confirmed", "travel history", "returned",
                          "government", "permanent", "pension"],
        "tips": {
            "weak": "Don't say 'please' or beg. State FACTS: 'I have confirmed tickets, a government job, and a baby waiting at home.'",
            "okay": "Good pitch. Make it tighter — 3 strongest facts in one sentence.",
            "strong": None
        }
    },
    "intent": {
        "must_have": ["clear no", "reason why not"],
        "good_keywords": ["no", "never", "india", "permanent", "pension", "government",
                          "family", "settle", "home", "not interested", "my country"],
        "tips": {
            "weak": "Be firm: 'No. My career, family, and pension are all in India. I have no reason to leave.'",
            "okay": "Good. Reinforce with specifics — government pension, family, property.",
            "strong": None
        }
    },
    "bank_balance": {
        "must_have": ["exact amount", "proof available"],
        "good_keywords": ["lakh", "savings", "bank", "statement", "balance", "amount",
                          "enough", "sufficient", "cover", "can show"],
        "tips": {
            "weak": "Give the exact balance: 'I have X lakh in my account. Here's the statement.'",
            "okay": "You gave a number. Offer to show the statement without being asked.",
            "strong": None
        }
    },
    "sponsor": {
        "must_have": ["who is paying", "source of funds"],
        "good_keywords": ["myself", "self", "own", "savings", "salary", "no sponsor",
                          "paying", "fund", "saved", "my money", "personal"],
        "tips": {
            "weak": "Be clear: 'I'm paying for everything myself from my salary and savings.'",
            "okay": "Good. Mention how long you saved and that the funds are verifiable.",
            "strong": None
        }
    },
    "property": {
        "must_have": ["yes/no", "details if yes"],
        "good_keywords": ["house", "land", "property", "flat", "apartment", "own", "registered",
                          "name", "plot", "agriculture", "farm", "investment"],
        "tips": {
            "weak": "If you own property, name it: 'I own a flat in [city] registered in my name.'",
            "okay": "Good. Mention approximate value if it strengthens your case.",
            "strong": None
        }
    },
    "role_detail": {
        "must_have": ["specific role", "responsibilities"],
        "good_keywords": ["ministry", "communication", "role", "position", "department", "manage",
                          "responsibility", "officer", "handle", "team", "report"],
        "tips": {
            "weak": "Describe your actual role: 'I handle [X] at the Ministry of Communications.'",
            "okay": "Good detail. Mention seniority or team size to show importance.",
            "strong": None
        }
    },
    "why_houston": {
        "must_have": ["match location", "reason"],
        "good_keywords": ["match", "portugal", "congo", "stadium", "nrg", "venue", "fifa",
                          "allocated", "scheduled", "that's where"],
        "tips": {
            "weak": "Simple: 'My match — Portugal vs Congo — is scheduled at NRG Stadium in Houston on June 17th.'",
            "okay": "Good. Add that you chose this based on the FIFA schedule, not random preference.",
            "strong": None
        }
    },
    "ticket_booking": {
        "must_have": ["how booked", "proof"],
        "good_keywords": ["fifa", "portal", "official", "website", "lottery", "bought", "paid",
                          "confirmation", "booked", "online", "app"],
        "tips": {
            "weak": "Say: 'I booked through the official FIFA portal. I have the confirmation email.'",
            "okay": "Good. Mention the cost to show financial commitment.",
            "strong": None
        }
    },
    "spouse_travel": {
        "must_have": ["clear answer", "reason"],
        "good_keywords": ["wife", "husband", "spouse", "baby", "child", "home", "work",
                          "staying", "not coming", "together", "yes"],
        "tips": {
            "weak": "Be clear why your spouse isn't coming — baby care, work, etc.",
            "okay": "Good reason. This actually shows ties — your family is waiting at home.",
            "strong": None
        }
    },
    "ties_single": {
        "must_have": ["concrete ties", "obligations"],
        "good_keywords": ["job", "career", "property", "parents", "family", "business",
                          "investment", "loan", "mortgage", "obligations"],
        "tips": {
            "weak": "Stack everything: job, parents who depend on you, property, career growth, financial obligations.",
            "okay": "Good. Emphasize things that BIND you — loans, responsibilities, career trajectory.",
            "strong": None
        }
    },
    "education": {
        "must_have": ["degree", "institution"],
        "good_keywords": ["degree", "university", "college", "graduated", "studied", "bachelor",
                          "master", "engineering", "science", "arts"],
        "tips": {
            "weak": "State your degree and university clearly.",
            "okay": "Good. Connect your education to your current career to show stability.",
            "strong": None
        }
    },
    "us_contact": {
        "must_have": ["relationship", "purpose of contact"],
        "good_keywords": ["friend", "relative", "colleague", "host", "hotel", "know",
                          "relationship", "staying"],
        "tips": {
            "weak": "Explain clearly who they are and how you know them.",
            "okay": "Good. Make sure to clarify you're NOT dependent on them for housing/support if staying in a hotel.",
            "strong": None
        }
    },
}


def get_instant_feedback(answer, question_key, score):
    """Get real-time coaching feedback for an answer."""
    lower = answer.lower()
    wc = len(answer.split())
    criteria = ANSWER_CRITERIA.get(question_key, {})
    good_kw = criteria.get("good_keywords", [])
    tips = criteria.get("tips", {})

    # Count keyword hits
    hits = sum(1 for kw in good_kw if kw in lower) if good_kw else 0
    total = len(good_kw) if good_kw else 1
    hit_ratio = hits / total

    # Determine rating
    if score >= 70 and wc >= 12 and hit_ratio >= 0.2:
        rating = "strong"
        emoji = "✅"
        tip = tips.get("strong", "Excellent answer. Confident, specific, and on point.")
        what_to_add = None
    elif score >= 45 and wc >= 6:
        rating = "okay"
        emoji = "⚠️"
        tip = tips.get("okay", "Decent answer but could be more specific.")
        # Figure out what's missing
        missing = []
        for must in criteria.get("must_have", []):
            missing.append(must)
        what_to_add = f"Try adding: {', '.join(missing[:2])}" if missing else None
    else:
        rating = "weak"
        emoji = "❌"
        tip = tips.get("weak", "Too vague or too short. Give specific details.")
        what_to_add = "Give a longer, more detailed answer with specific facts and numbers."

    # Extra penalties
    if wc < 4:
        tip = "Way too short! A one-line answer in a visa interview is a red flag."
        what_to_add = "Expand your answer to at least 2-3 sentences."
        rating = "weak"
        emoji = "❌"

    vague_words = ['maybe', 'i think', 'probably', 'not sure', 'i guess', 'umm', 'uhh']
    if any(v in lower for v in vague_words):
        tip = (tip or "") + " Remove uncertain words like 'maybe', 'I think', 'probably'."
        if rating == "strong":
            rating = "okay"
            emoji = "⚠️"

    return {
        "rating": rating,
        "emoji": emoji,
        "tip": tip or "Keep practicing.",
        "what_to_add": what_to_add,
    }


# --- Difficulty modifiers ---
DIFFICULTY_SETTINGS = {
    "easy": {
        "follow_up_chance": 0.15,
        "max_follow_ups": 1,
        "reactions_pool": "good",
        "score_bonus": 10,
        "max_questions": 7,
        "description": "Friendly officer — fewer follow-ups, more forgiving",
    },
    "medium": {
        "follow_up_chance": 0.35,
        "max_follow_ups": 3,
        "reactions_pool": "mixed",
        "score_bonus": 0,
        "max_questions": 9,
        "description": "Balanced — realistic interview pace",
    },
    "hard": {
        "follow_up_chance": 0.55,
        "max_follow_ups": 5,
        "reactions_pool": "skeptical",
        "score_bonus": -10,
        "max_questions": 11,
        "description": "Hostile officer — aggressive follow-ups, interrupts, very strict",
    },
}


def get_difficulty_settings(level):
    """Get difficulty modifier settings."""
    return DIFFICULTY_SETTINGS.get(level, DIFFICULTY_SETTINGS["medium"])
