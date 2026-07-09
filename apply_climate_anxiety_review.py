import json
from pathlib import Path

review_path = Path("temp/queries/climate_anxiety_2026/review/review_table.json")
rows = json.loads(review_path.read_text())

decisions = {
    "PMC12959560": ("include", "Climate anxiety in vulnerable, young population"),
    "PMC13223078": ("exclude", "Broader planetary health framing, anxiety mentioned very briefly"),
    "PMC12789392": ("include", "Climate anxiety in pediatric ED setting"),
    "PMC12802099": ("include", "Linking climate events to mental health outcomes"),
    "PMC12832621": ("include", "Cross-sectional study on climate related psychological distress"),
    "PMC12841537": ("include", "Qualitative study on climate worry/distress and coping barriers"),
    "PMC12855563": ("review", "About workforce strain/service delivery, not personal anxiety - tangential"),
    "PMC12857198": ("exclude", "About physical activity research framing, no climate/anxiety content"),
    "PMC12868119": ("exclude", "Confirmed via full text: climate anxiety mentioned once in passing list, not the subject"),
    "PMC12925469": ("review", "General youth mental health dataset, climate link not stated"),
    "PMC12935418": ("review", "About heat-related public discourse/sentiment, not anxiety specifically"),
    "PMC12972113": ("include", "Phenomenological study directly on climate crisis and mental health disorders"),
    "PMC13017450": ("exclude", "Confirmed via full text: multi-article newsletter, climate mentioned once in passing"),
    "PMC13033858": ("include", "Explicitly studies climate anxiety and coping strategies"),
    "PMC13064374": ("include", "Quantitative study directly measuring climate anxiety determinants"),
    "PMC13089125": ("include", "Clinical context study on climate-related mental health impacts"),
    "PMC13092825": ("include", "Pilot trial specifically targeting eco-anxiety coping in children"),
    "PMC13092878": ("include", "Links climate exposure to psychological distress/aggression"),
    "PMC13093722": ("include", "Commentary directly on climate mental health risks for vulnerable groups"),
    "PMC13112313": ("include", "Multinational study explicitly on climate anxiety mechanisms"),
    "PMC13116603": ("exclude", "About meteorosensitivity/meteoropathy, different construct from climate anxiety"),
    "PMC13122536": ("include", "Scoping review on climate-related psychological distress"),
    "PMC13143408": ("include", "Direct empirical study on climate worry and mental health"),
    "PMC13147318": ("include", "Systematic review/meta-analysis directly on eco-anxiety"),
    "PMC13151464": ("exclude", "About emissions reduction strategy, not psychological anxiety"),
    "PMC13185269": ("include", "Direct empirical study linking anxiety to climate action"),
    "PMC13190411": ("review", "About counselling practice/planetary health, anxiety not the direct subject"),
    "PMC13192185": ("include", "Direct study on climate anxiety influencing reproductive decisions"),
    "PMC13200154": ("exclude", "General psychiatric diagnosis critique, no climate content"),
    "PMC13205920": ("include", "Cross-sectional study directly measuring climate-related anxiety"),
    "PMC13205934": ("include", "Direct study on climate anxiety mediated by ecological awareness"),
    "PMC13217755": ("include", "Scoping review specifically on climate anxiety in this population"),
    "PMC13241739": ("include", "Direct study on climate anxiety factors in a specific population"),
    "PMC13247379": ("include", "Direct study on multiple eco-emotions in a climate-vulnerable population"),
    "PMC13254375": ("include", "Case report directly linking climate change to psychiatric crisis"),
    "PMC13289144": ("include", "Perspective piece directly on climate change's mental health impact"),
    "PMC12872338": ("include", "Development of a climate anxiety measurement tool"),
    "PMC12892733": ("exclude", "Ethical climate = workplace culture, not environmental climate - false positive"),
    "PMC12899786": ("include", "Direct study on eco-anxiety and related behavioral factors"),
    "PMC12993146": ("include", "Direct study on youth psychosocial response to climate change"),
    "PMC13023394": ("include", "Title is a direct, unambiguous match"),
    "PMC13041367": ("review", "Climate mentioned alongside AI/migration as one of several factors - tangential"),
    "PMC13133856": ("include", "Discusses psychological fears specifically tied to the eco-crisis"),
    "PMC13178203": ("include", "Direct study on youth engagement/motivation re: climate crisis"),
    "PMC13203639": ("review", "Related construct but framed around career choice, not general anxiety"),
    "PMC13231233": ("include", "Direct study on eco-anxiety following a specific climate event"),
    "PMC13235141": ("include", "Eco-anxiety explicitly modeled as a mediating factor"),
    "PMC13297762": ("exclude", "No climate anxiety content, about food choice emotions only"),
    "PMC13299314": ("include", "Direct empirical study on climate worry and wellbeing"),
    "PMC13176867": ("include", "Directly addresses methodological issues in climate anxiety research"),
}

updated = 0
for row in rows:
    pmcid = row.get("pmcid", "")
    if pmcid in decisions:
        status, note = decisions[pmcid]
        row["review_status"] = status
        row["review_notes"] = note
        updated += 1

review_path.write_text(json.dumps(rows, indent=2))
print(f"Updated {updated} of {len(rows)} rows")
