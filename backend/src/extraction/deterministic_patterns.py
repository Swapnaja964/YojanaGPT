import re

STATE_PATTERN = re.compile(r"(?:resident|residing|native|residing in|domiciled in)\s+(?:of\s+)?(?P<state>[A-Za-z &]+)", re.IGNORECASE)
OCCUPATION_PATTERN = re.compile(r"(?:applicant|beneficiary|person|candidate|farmer|fisherman|worker|student)[^\.\n]{0,40}?(?:should|must|shall|is required to)\s+(?:be\s+an?\s+)?(?P<occ>[A-Za-z &]+)", re.IGNORECASE)
AGE_PATTERN = re.compile(r"(?P<min>\d{1,2})\s*(?:-|to|–|—)\s*(?P<max>\d{1,2})\s*years", re.IGNORECASE)
AGE_SINGLE = re.compile(r"aged?\s*(?:between\s*)?(?P<min>\d{1,2})\s*(?:and|-|to)\s*(?P<max>\d{1,2})", re.IGNORECASE)
INCOME_PATTERN = re.compile(r"(?:income|annual income|family income)[^\d]{0,40}?(?:not exceed|not exceed[s]?|less than|below|<=|under)\s*₹?\s*(?P<amt>[\d,]+(?:\.\d+)?)", re.IGNORECASE)
INCOME_LAKH = re.compile(r"(?P<num>[\d\.]+)\s*(?:lakh|lac|lakhs|lacs)", re.IGNORECASE)
CATEGORY_PATTERN = re.compile(r"\b(SC|ST|OBC|General|Brahmin|Scheduled Tribe|Scheduled Caste)\b", re.IGNORECASE)
LAND_PATTERN = re.compile(r"(?P<area>[\d\.]+)\s*(?:hectare|hectares|ha|acre|acres)", re.IGNORECASE)
REG_PATTERN = re.compile(r"(?:registered with|registered under|enrolled with|member of)\s+(?P<body>[A-Za-z0-9 &/()'-]+)", re.IGNORECASE)
REL_PATTERN = re.compile(r"\b(legal heir|spouse|son|daughter|parent|brother|sister|next of kin|dependent)\b", re.IGNORECASE)
DATE_YEAR_PATTERN = re.compile(r"(?P<when>on|after|before|from|since)\s+(?P<year>20\d{2})", re.IGNORECASE)

def _to_int_amount(s):
    s = s.replace(",", "").strip()
    try:
        return int(float(s))
    except:
        return None

def _convert_lakh_phrase(text):
    m = INCOME_LAKH.search(text)
    if m:
        try:
            return int(float(m.group("num")) * 100000)
        except:
            return None
    return None

def extract_deterministic_rules(text: str):
    if not text:
        return []
    t = text
    rules = []

    # State
    m = STATE_PATTERN.search(t)
    if m:
        state = m.group("state").strip().rstrip(".")
        rules.append({"field":"state","operator":"=","value":state,"text_span":m.group(0),"confidence":0.9,"source":"regex"})

    # Occupation
    m = OCCUPATION_PATTERN.search(t)
    if m:
        occ = m.group("occ").strip().rstrip(".")
        rules.append({"field":"occupation","operator":"=","value":occ,"text_span":m.group(0),"confidence":0.9,"source":"regex"})

    # Age range
    m = AGE_PATTERN.search(t) or AGE_SINGLE.search(t)
    if m:
        try:
            mn = int(m.group("min"))
            mx = int(m.group("max"))
            rules.append({"field":"age","operator":"between","value":[mn,mx],"text_span":m.group(0),"confidence":0.9,"source":"regex"})
        except:
            pass

    # Income
    m = INCOME_PATTERN.search(t)
    if m:
        amt = _to_int_amount(m.group("amt"))
        if amt is None:
            lk = _convert_lakh_phrase(t)
            if lk:
                amt = lk
        if amt:
            rules.append({"field":"income_annual","operator":"<=","value":amt,"text_span":m.group(0),"confidence":0.9,"source":"regex"})

    # Category
    m = CATEGORY_PATTERN.search(t)
    if m:
        cat = m.group(0).strip()
        cat = cat.replace("Scheduled Tribe","ST").replace("Scheduled Caste","SC")
        rules.append({"field":"category","operator":"=","value":cat,"text_span":m.group(0),"confidence":0.9,"source":"regex"})

    # Land
    m = LAND_PATTERN.search(t)
    if m:
        try:
            area = float(m.group("area"))
            unit = m.group(0).lower()
            if "acre" in unit:
                area = area * 0.404686
            rules.append({"field":"land_area_ha","operator":">=","value":round(area,3),"text_span":m.group(0),"confidence":0.9,"source":"regex"})
        except:
            pass

    # Registration body
    m = REG_PATTERN.search(t)
    if m:
        body = m.group("body").strip().rstrip(".")
        rules.append({"field":"registered_with","operator":"=","value":body,"text_span":m.group(0),"confidence":0.9,"source":"regex"})

    # Relation
    m = REL_PATTERN.search(t)
    if m:
        rules.append({"field":"relation","operator":"contains","value":m.group(0).lower(),"text_span":m.group(0),"confidence":0.9,"source":"regex"})

    # Year constraints
    m = DATE_YEAR_PATTERN.search(t)
    if m:
        try:
            yr = int(m.group("year"))
            rules.append({"field":"year","operator":m.group("when"),"value":yr,"text_span":m.group(0),"confidence":0.9,"source":"regex"})
        except:
            pass

    return rules
