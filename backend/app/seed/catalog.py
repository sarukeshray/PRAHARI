"""Static catalogues the synthetic generator draws from.

Place names are real so the map and district filters look plausible. Every
person, agency, work and rupee figure produced from these catalogues is
invented — no MP name here corresponds to any sitting member, and no agency
name to any real office.
"""

from app.models.enums import AgencyType, Terrain, UserAgencyType

# --------------------------------------------------------------------------
# Geography
# --------------------------------------------------------------------------

# (district_id, name, state, terrain, lat, lon)
DISTRICTS: list[tuple[str, str, str, Terrain, float, float]] = [
    ("RJ-UDR", "Udaipur", "Rajasthan", Terrain.HILLY, 24.5854, 73.7125),
    ("RJ-BMR", "Barmer", "Rajasthan", Terrain.REMOTE, 25.7521, 71.3967),
    ("RJ-JPR", "Jaipur", "Rajasthan", Terrain.URBAN, 26.9124, 75.7873),
    ("RJ-BHL", "Bhilwara", "Rajasthan", Terrain.PLAIN, 25.3407, 74.6313),
    ("KL-IDK", "Idukki", "Kerala", Terrain.HILLY, 9.8497, 76.9681),
    ("KL-ALP", "Alappuzha", "Kerala", Terrain.COASTAL, 9.4981, 76.3388),
    ("KL-EKM", "Ernakulam", "Kerala", Terrain.URBAN, 9.9816, 76.2999),
    ("KL-PKD", "Palakkad", "Kerala", Terrain.PLAIN, 10.7867, 76.6548),
    ("MP-CHW", "Chhindwara", "Madhya Pradesh", Terrain.PLAIN, 22.0574, 78.9382),
    ("MP-REW", "Rewa", "Madhya Pradesh", Terrain.PLAIN, 24.5362, 81.3037),
    ("MP-BPL", "Bhopal", "Madhya Pradesh", Terrain.URBAN, 23.2599, 77.4126),
    ("MP-MDL", "Mandla", "Madhya Pradesh", Terrain.REMOTE, 22.5980, 80.3714),
]

BLOCKS: dict[str, list[str]] = {
    "RJ-UDR": ["Girwa", "Badgaon", "Mavli", "Vallabhnagar", "Kherwara", "Sarada", "Jhadol", "Kotra"],
    "RJ-BMR": ["Barmer", "Baytu", "Sheo", "Sindhari", "Chohtan", "Ramsar", "Gudamalani"],
    "RJ-JPR": ["Sanganer", "Amber", "Bassi", "Chaksu", "Jamwa Ramgarh", "Phagi", "Dudu"],
    "RJ-BHL": ["Mandal", "Hurda", "Shahpura", "Jahazpur", "Asind", "Banera", "Raipur"],
    "KL-IDK": ["Devikulam", "Udumbanchola", "Thodupuzha", "Peermade", "Idukki", "Azhutha"],
    "KL-ALP": ["Ambalappuzha", "Cherthala", "Kuttanad", "Karthikappally", "Mavelikkara"],
    "KL-EKM": ["Kanayannur", "Aluva", "Paravur", "Kunnathunad", "Muvattupuzha", "Kothamangalam"],
    "KL-PKD": ["Palakkad", "Chittur", "Alathur", "Ottapalam", "Mannarkkad", "Pattambi"],
    "MP-CHW": ["Chhindwara", "Parasia", "Amarwara", "Sausar", "Pandhurna", "Junnardeo"],
    "MP-REW": ["Huzur", "Sirmour", "Teonthar", "Mauganj", "Hanumana", "Raipur Karchuliyan"],
    "MP-BPL": ["Huzur", "Berasia", "Phanda", "Kolar", "Govindpura"],
    "MP-MDL": ["Mandla", "Nainpur", "Bichhiya", "Niwas", "Ghughri", "Mawai"],
}

# --------------------------------------------------------------------------
# Works and rates
# --------------------------------------------------------------------------

# work_type -> (unit, base plain-terrain rate in rupees for a typical work, plain-language name)
#
# Sized to actual MPLADS works, which are small: a typical sanction is a few
# lakh, not a few crore. Getting this wrong made 40 members breach the annual
# 5 crore entitlement by accident, drowning the finding meant to surface it.
WORK_TYPES: dict[str, tuple[str, float, str]] = {
    "ROAD_CC": ("per km", 1_890_000, "cement concrete road"),
    "ROAD_BT": ("per km", 1_395_000, "bituminous road"),
    "COMMUNITY_HALL": ("per unit", 832_500, "community hall"),
    "SCHOOL_BUILDING": ("per room", 427_500, "school building"),
    "WATER_TANK": ("per unit", 517_500, "water storage tank"),
    "BOREWELL": ("per unit", 216_000, "borewell"),
    "STREET_LIGHTING": ("per 10 poles", 144_000, "street lighting"),
    "DRAINAGE": ("per 100 m", 184_500, "drainage line"),
    "TOILET_BLOCK": ("per unit", 279_000, "toilet block"),
    "LIBRARY": ("per unit", 630_000, "library building"),
    "BUS_SHELTER": ("per unit", 126_000, "bus shelter"),
    "CREMATORIUM_SHED": ("per unit", 243_000, "crematorium shed"),
}

# Work types outside the MPLADS permissible list, used only to construct the
# CAG-01 backtest case. Never generated in the ordinary population.
IMPERMISSIBLE_WORK_TYPES = [
    "OFFICE_RENOVATION",
    "BOUNDARY_WALL_PRIVATE_TRUST",
    "MEMORIAL_STATUE",
    "PLACE_OF_WORSHIP_REPAIR",
]

TERRAIN_MULTIPLIER: dict[Terrain, float] = {
    Terrain.PLAIN: 1.00,
    Terrain.COASTAL: 1.10,
    Terrain.URBAN: 1.18,
    Terrain.HILLY: 1.28,
    Terrain.REMOTE: 1.42,
}

# Annual Schedule of Rates escalation. Because a work is compared against the
# rate for its own year, this escalation cancels out of the ratio entirely —
# which is exactly the inflation defence the engine relies on.
SOR_ANNUAL_ESCALATION = 0.062
SOR_BASE_YEAR = 2023
SOR_YEARS = [2023, 2024, 2025, 2026]

# Illustrative construction cost index, used only for the real-terms view.
COST_INDEX = {2023: 100.0, 2024: 106.4, 2025: 113.1, 2026: 120.2}

# Round sanction thresholds a split work is priced just underneath.
SANCTION_THRESHOLDS = [500_000, 1_000_000, 2_500_000]

# --------------------------------------------------------------------------
# Description phrase bank
# --------------------------------------------------------------------------
# Templated so realistic near-duplicates arise naturally rather than being
# manufactured — two officers describing the same road will write similar text.

DESC_ACTION = [
    "Construction of",
    "Providing and laying",
    "Development of",
    "Erection of",
    "Construction and commissioning of",
]

DESC_DETAIL: dict[str, list[str]] = {
    "ROAD_CC": [
        "cement concrete road with side drains",
        "CC road including earthwork and kerb stones",
        "concrete village road with cross drainage",
    ],
    "ROAD_BT": [
        "bituminous surfacing over existing WBM road",
        "black-topped approach road with shoulders",
        "BT road including premix carpeting",
    ],
    "COMMUNITY_HALL": [
        "community hall with RCC roof and boundary wall",
        "multipurpose community building with verandah",
        "panchayat community hall with toilet block",
    ],
    "SCHOOL_BUILDING": [
        "two additional classrooms with attached verandah",
        "school building with RCC slab and flooring",
        "additional classroom block with furniture",
    ],
    "WATER_TANK": [
        "RCC overhead water storage tank with pump house",
        "elevated water storage tank of 20,000 litre capacity",
        "overhead tank with distribution pipeline",
    ],
    "BOREWELL": [
        "borewell with submersible pump and platform",
        "deep borewell including motor and casing pipe",
        "tubewell with concrete platform and soak pit",
    ],
    "STREET_LIGHTING": [
        "solar LED street lights with poles",
        "street lighting with GI poles and fittings",
        "LED street light installation along the main road",
    ],
    "DRAINAGE": [
        "covered pucca drainage line with slabs",
        "RCC drainage channel with silt chambers",
        "pucca nali with covering slabs",
    ],
    "TOILET_BLOCK": [
        "community toilet block with septic tank",
        "public sanitation block with water connection",
        "ten-seat toilet block with soak pit",
    ],
    "LIBRARY": [
        "village reading room and library building",
        "library building with furniture and shelving",
        "public reading room with study hall",
    ],
    "BUS_SHELTER": [
        "passenger bus shelter with seating",
        "bus waiting shed with roof sheeting",
        "roadside passenger shelter with benches",
    ],
    "CREMATORIUM_SHED": [
        "covered crematorium shed with approach path",
        "cremation ground shed with water point",
        "shed at cremation ground including platform",
    ],
}

DESC_LOCATION = [
    "at {panchayat} village",
    "in {panchayat} panchayat",
    "near the {panchayat} primary school",
    "at {panchayat}, ward {ward}",
    "on the {panchayat} approach road",
]

DESC_SUFFIX = [
    "under the MPLAD Scheme.",
    "as recommended under MPLADS.",
    "to serve the surrounding habitations.",
    "for the benefit of local residents.",
    "including all incidental works.",
]

# --------------------------------------------------------------------------
# Names — all fictional
# --------------------------------------------------------------------------

MP_FIRST = ["A.", "K.", "R.", "S.", "M.", "P.", "V.", "N.", "D.", "T.", "B.", "G."]
MP_LAST = [
    "Vaishnav", "Meena", "Purohit", "Nair", "Rathore", "Chauhan", "Menon", "Pillai",
    "Yadav", "Tiwari", "Shukla", "Patel", "Verma", "Joshi", "Kurup", "Sharma",
    "Bhargava", "Solanki", "Thomas", "Reddy",
]
MP_HONORIFIC = ["Dr.", "Shri", "Smt.", "Prof."]

AGENCY_TEMPLATES: list[tuple[str, AgencyType]] = [
    ("PWD Division {district}", AgencyType.PWD),
    ("Zila Parishad {district}", AgencyType.PRI),
    ("Nagar Palika {district}", AgencyType.MUNICIPAL),
    ("PHED Division {district}", AgencyType.LINE_DEPARTMENT),
    ("Rural Engineering Service {district}", AgencyType.LINE_DEPARTMENT),
]

USER_AGENCY_TEMPLATES: list[tuple[str, UserAgencyType]] = [
    ("Government Higher Secondary School, {block}", UserAgencyType.SCHOOL),
    ("Gram Panchayat {block}", UserAgencyType.PANCHAYAT),
    ("Primary Health Centre, {block}", UserAgencyType.HEALTH_CENTRE),
    ("Municipal Ward Office, {block}", UserAgencyType.MUNICIPAL_BODY),
]

OFFICER_NAMES = [
    "S. Nair", "R. Deshmukh", "A. Krishnan", "M. Bhatt", "P. Ranganathan",
    "K. Iyer", "V. Chandran", "N. Saxena", "T. Balan", "D. Rawal",
]
