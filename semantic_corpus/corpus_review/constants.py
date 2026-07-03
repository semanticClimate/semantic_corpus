"""Constants for corpus review workflow (no magic strings)."""

REVIEW_STATUS_INCLUDE = "include"
REVIEW_STATUS_REVIEW = "review"
REVIEW_STATUS_EXCLUDE = "exclude"

VALID_REVIEW_STATUSES = (
    REVIEW_STATUS_INCLUDE,
    REVIEW_STATUS_REVIEW,
    REVIEW_STATUS_EXCLUDE,
)

DEFAULT_REVIEW_STATUS = REVIEW_STATUS_REVIEW

INDIA_LOCATION_TERMS = (
    "india",
    "indian",
    "delhi",
    "mumbai",
    "kolkata",
    "chennai",
    "bengaluru",
    "bangalore",
    "hyderabad",
    "ahmedabad",
    "lucknow",
    "kanpur",
    "patna",
    "pune",
    "jaipur",
    "uttar pradesh",
    "maharashtra",
    "west bengal",
    "tamil nadu",
    "karnataka",
)

POLLUTANT_TERMS = (
    "aqi",
    "air quality index",
    "pm2.5",
    "pm10",
    "pm 2.5",
    "pm 10",
    "particulate matter",
    "ambient air pollution",
    "air pollution",
    "no2",
    "so2",
    "o3",
    "ozone",
    "carbon monoxide",
)

HEALTH_TERMS = (
    "exposure",
    "mortality",
    "morbidity",
    "respiratory",
    "cardiovascular",
    "health",
    "epidemiology",
    "public health",
)

CLIMATE_TERMS = (
    "climate change",
    "climate",
    "global warming",
    "greenhouse gas",
    "ghg",
    "carbon dioxide",
    "co2",
    "emissions",
    "mitigation",
    "adaptation",
    "warming",
    "carbon",
    "net zero",
    "decarbonisation",
    "decarbonization",
)

# Value used when a classification column has not been populated yet.
UNCLASSIFIED_LABEL = ""

REVIEW_TABLE_COLUMNS = (
    "review_status",
    "score",
    "paper_id",
    "pmcid",
    "pmid",
    "doi",
    "title",
    "publication_date",
    "journal",
    "authors",
    "has_xml",
    "has_pdf",
    "pdf_path",
    "query_name",
    "query_string",
    "location_terms",
    "pollutant_terms",
    "health_terms",
    "cluster_id",
    "cluster_terms",
    "encyclopedia_category",
    "encyclopedia_score",
    "encyclopedia_terms",
    "abstract_snippet",
    "review_notes",
)
