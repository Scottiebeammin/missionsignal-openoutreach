OPPORTUNITY_FOCUS_CATEGORIES = [
    "Veterans",
    "Homelessness",
    "Healthcare",
    "Mental Health",
    "LGBTQ+",
    "Disability",
    "Food Security",
    "Housing",
    "Reentry / Justice-Involved",
    "Youth Development",
    "Workforce Development",
    "Digital Equity",
    "Education",
    "Small Business",
    "Arts & Culture",
    "Community Development",
    "Senior Services",
    "Immigrant / Refugee Support",
    "Environmental Justice",
    "Rural Communities",
]

CATEGORY_KEYWORDS = {
    "Veterans": ("veteran", "veterans", "military", "service member"),
    "Homelessness": ("homeless", "homelessness", "shelter", "unhoused"),
    "Healthcare": ("healthcare", "health care", "medical", "clinic", "health"),
    "Mental Health": ("mental health", "behavioral health", "counseling", "trauma"),
    "LGBTQ+": ("lgbtq", "lgbtq+", "queer", "transgender"),
    "Disability": ("disability", "disabled", "accessibility", "neurodiverse"),
    "Food Security": ("food security", "food", "nutrition", "meal", "hunger"),
    "Housing": ("housing", "rent", "tenant", "eviction"),
    "Reentry / Justice-Involved": ("reentry", "justice-involved", "justice involved", "formerly incarcerated"),
    "Youth Development": ("youth", "young people", "children", "teen", "student"),
    "Workforce Development": ("workforce", "career", "employment", "job", "training"),
    "Digital Equity": ("digital equity", "digital divide", "broadband", "device access", "technology access"),
    "Education": ("education", "school", "student", "learning", "training"),
    "Small Business": ("small business", "entrepreneur", "entrepreneurship", "microenterprise"),
    "Arts & Culture": ("arts", "culture", "creative", "artist"),
    "Community Development": ("community development", "neighborhood", "resident services", "civic"),
    "Senior Services": ("senior", "older adult", "aging", "elder"),
    "Immigrant / Refugee Support": ("immigrant", "refugee", "new american", "asylum"),
    "Environmental Justice": ("environmental justice", "climate", "sustainability", "pollution"),
    "Rural Communities": ("rural", "rural communities", "rural residents"),
}


def canonical_category(value: str) -> str:
    clean = str(value).strip()
    if not clean:
        return ""
    folded = clean.casefold()
    for category in OPPORTUNITY_FOCUS_CATEGORIES:
        if folded == category.casefold():
            return category
        if folded in {keyword.casefold() for keyword in CATEGORY_KEYWORDS[category]}:
            return category
    return clean
