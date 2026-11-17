"""profiles: reference data, profiles, photos, preferences, delegation

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-17 10:34:47.936411
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

DT = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")

# (code, name_en, name_ta, [(city_code, city_en, city_ta), ...]) — city list starts with the HQ.
TN_DISTRICTS = [
    ("ariyalur", "Ariyalur", "அரியலூர்", []),
    ("chengalpattu", "Chengalpattu", "செங்கல்பட்டு", [("tambaram", "Tambaram", "தாம்பரம்")]),
    ("chennai", "Chennai", "சென்னை", []),
    ("coimbatore", "Coimbatore", "கோயம்புத்தூர்", [("pollachi", "Pollachi", "பொள்ளாச்சி")]),
    ("cuddalore", "Cuddalore", "கடலூர்", [("chidambaram", "Chidambaram", "சிதம்பரம்")]),
    ("dharmapuri", "Dharmapuri", "தருமபுரி", []),
    ("dindigul", "Dindigul", "திண்டுக்கல்", [("palani", "Palani", "பழனி")]),
    ("erode", "Erode", "ஈரோடு", [("gobichettipalayam", "Gobichettipalayam", "கோபிசெட்டிபாளையம்")]),
    ("kallakurichi", "Kallakurichi", "கள்ளக்குறிச்சி", []),
    ("kancheepuram", "Kancheepuram", "காஞ்சிபுரம்", []),
    ("kanyakumari", "Kanyakumari", "கன்னியாகுமரி", [("nagercoil", "Nagercoil", "நாகர்கோவில்")]),
    ("karur", "Karur", "கரூர்", []),
    ("krishnagiri", "Krishnagiri", "கிருஷ்ணகிரி", [("hosur", "Hosur", "ஓசூர்")]),
    ("madurai", "Madurai", "மதுரை", []),
    ("mayiladuthurai", "Mayiladuthurai", "மயிலாடுதுறை", []),
    ("nagapattinam", "Nagapattinam", "நாகப்பட்டினம்", []),
    ("namakkal", "Namakkal", "நாமக்கல்", [("tiruchengode", "Tiruchengode", "திருச்செங்கோடு")]),
    (
        "nilgiris",
        "Nilgiris",
        "நீலகிரி",
        [("ooty", "Udhagamandalam (Ooty)", "உதகமண்டலம்"), ("coonoor", "Coonoor", "குன்னூர்")],
    ),
    ("perambalur", "Perambalur", "பெரம்பலூர்", []),
    ("pudukkottai", "Pudukkottai", "புதுக்கோட்டை", []),
    ("ramanathapuram", "Ramanathapuram", "இராமநாதபுரம்", []),
    ("ranipet", "Ranipet", "இராணிப்பேட்டை", []),
    ("salem", "Salem", "சேலம்", []),
    ("sivaganga", "Sivaganga", "சிவகங்கை", [("karaikudi", "Karaikudi", "காரைக்குடி")]),
    ("tenkasi", "Tenkasi", "தென்காசி", []),
    ("thanjavur", "Thanjavur", "தஞ்சாவூர்", [("kumbakonam", "Kumbakonam", "கும்பகோணம்")]),
    ("theni", "Theni", "தேனி", []),
    ("thoothukudi", "Thoothukudi", "தூத்துக்குடி", []),
    ("tiruchirappalli", "Tiruchirappalli", "திருச்சிராப்பள்ளி", []),
    ("tirunelveli", "Tirunelveli", "திருநெல்வேலி", []),
    ("tirupathur", "Tirupathur", "திருப்பத்தூர்", []),
    ("tiruppur", "Tiruppur", "திருப்பூர்", []),
    ("tiruvallur", "Tiruvallur", "திருவள்ளூர்", [("avadi", "Avadi", "ஆவடி")]),
    ("tiruvannamalai", "Tiruvannamalai", "திருவண்ணாமலை", []),
    ("tiruvarur", "Tiruvarur", "திருவாரூர்", []),
    ("vellore", "Vellore", "வேலூர்", []),
    ("viluppuram", "Viluppuram", "விழுப்புரம்", []),
    (
        "virudhunagar",
        "Virudhunagar",
        "விருதுநகர்",
        [("sivakasi", "Sivakasi", "சிவகாசி"), ("rajapalayam", "Rajapalayam", "இராஜபாளையம்")],
    ),
]

OTHER_STATES = [
    ("puducherry", "Puducherry", "புதுச்சேரி"),
    ("karnataka", "Karnataka", "கர்நாடகா"),
    ("kerala", "Kerala", "கேரளா"),
    ("andhra_pradesh", "Andhra Pradesh", "ஆந்திரப் பிரதேசம்"),
    ("telangana", "Telangana", "தெலங்கானா"),
    ("maharashtra", "Maharashtra", "மகாராஷ்டிரா"),
    ("delhi", "Delhi", "தில்லி"),
    ("other", "Other state", "பிற மாநிலம்"),
]

COUNTRIES = [
    ("IN", "India", "இந்தியா"),
    ("US", "United States", "அமெரிக்கா"),
    ("GB", "United Kingdom", "ஐக்கிய இராச்சியம்"),
    ("CA", "Canada", "கனடா"),
    ("AU", "Australia", "ஆஸ்திரேலியா"),
    ("NZ", "New Zealand", "நியூசிலாந்து"),
    ("SG", "Singapore", "சிங்கப்பூர்"),
    ("MY", "Malaysia", "மலேசியா"),
    ("LK", "Sri Lanka", "இலங்கை"),
    ("AE", "United Arab Emirates", "ஐக்கிய அரபு அமீரகம்"),
    ("SA", "Saudi Arabia", "சவூதி அரேபியா"),
    ("QA", "Qatar", "கத்தார்"),
    ("DE", "Germany", "ஜெர்மனி"),
]

# PLACEHOLDER community taxonomy — replace via admin once the launch community is confirmed
# (PRD §18.1). Codes are stable; labels can be edited without code changes.
COMMUNITY = ("launch_community", "Launch community (placeholder)", "தொடக்கச் சமூகம் (தற்காலிகம்)")
SUB_COMMUNITIES = [
    ("sub_a", "Sub-group A (placeholder)", "உட்பிரிவு அ (தற்காலிகம்)"),
    ("sub_b", "Sub-group B (placeholder)", "உட்பிரிவு ஆ (தற்காலிகம்)"),
    ("sub_c", "Sub-group C (placeholder)", "உட்பிரிவு இ (தற்காலிகம்)"),
    ("not_specified", "Prefer not to specify", "குறிப்பிட விரும்பவில்லை"),
]


revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "community_taxonomy",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("label_en", sa.String(length=150), nullable=False),
        sa.Column("label_ta", sa.String(length=150), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["community_taxonomy.id"],
            name=op.f("fk_community_taxonomy_parent_id_community_taxonomy"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_community_taxonomy")),
        sa.UniqueConstraint("type", "code", name=op.f("uq_community_taxonomy_type_code")),
    )
    op.create_table(
        "locations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name_en", sa.String(length=100), nullable=False),
        sa.Column("name_ta", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["locations.id"],
            name=op.f("fk_locations_parent_id_locations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_locations")),
        sa.UniqueConstraint("code", name=op.f("uq_locations_code")),
    )
    op.create_index(
        "ix_locations_parent_type", "locations", ["parent_id", "type", "active"], unique=False
    )
    op.create_table(
        "profiles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=True),
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("subject_phone_e164", sa.String(length=16), nullable=True),
        sa.Column("created_for", sa.String(length=20), nullable=False),
        sa.Column("subject_name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=60), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(length=10), nullable=True),
        sa.Column("marital_status", sa.String(length=30), nullable=True),
        sa.Column("has_children", sa.Boolean(), nullable=True),
        sa.Column("height_cm", sa.SmallInteger(), nullable=True),
        sa.Column("mother_tongue", sa.String(length=30), nullable=True),
        sa.Column("current_country", sa.String(length=2), nullable=True),
        sa.Column("state_id", sa.BigInteger(), nullable=True),
        sa.Column("district_id", sa.BigInteger(), nullable=True),
        sa.Column("city_id", sa.BigInteger(), nullable=True),
        sa.Column("profile_status", sa.String(length=20), nullable=False),
        sa.Column("status_reason_code", sa.String(length=50), nullable=True),
        sa.Column("status_note", sa.String(length=500), nullable=True),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("completion_percent", sa.SmallInteger(), nullable=False),
        sa.Column("submitted_at", DT, nullable=True),
        sa.Column("approved_at", DT, nullable=True),
        sa.Column("created_at", DT, nullable=False),
        sa.Column("updated_at", DT, nullable=False),
        sa.ForeignKeyConstraint(
            ["city_id"],
            ["locations.id"],
            name=op.f("fk_profiles_city_id_locations"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_profiles_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["district_id"],
            ["locations.id"],
            name=op.f("fk_profiles_district_id_locations"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name=op.f("fk_profiles_owner_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["state_id"],
            ["locations.id"],
            name=op.f("fk_profiles_state_id_locations"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profiles")),
        sa.UniqueConstraint("owner_user_id", name=op.f("uq_profiles_owner_user_id")),
        sa.UniqueConstraint("public_id", name=op.f("uq_profiles_public_id")),
    )
    op.create_index(
        op.f("ix_profiles_created_by_user_id"), "profiles", ["created_by_user_id"], unique=False
    )
    op.create_index(
        "ix_profiles_discovery",
        "profiles",
        ["profile_status", "visibility", "gender", "date_of_birth"],
        unique=False,
    )
    op.create_index("ix_profiles_location", "profiles", ["state_id", "district_id"], unique=False)
    op.create_index(
        op.f("ix_profiles_subject_phone_e164"), "profiles", ["subject_phone_e164"], unique=False
    )
    op.create_table(
        "delegated_access",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("delegate_user_id", sa.BigInteger(), nullable=True),
        sa.Column("invited_phone_e164", sa.String(length=16), nullable=True),
        sa.Column("invited_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("relationship", sa.String(length=20), nullable=False),
        sa.Column("permission_scope", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("invited_at", DT, nullable=False),
        sa.Column("accepted_at", DT, nullable=True),
        sa.Column("revoked_at", DT, nullable=True),
        sa.ForeignKeyConstraint(
            ["delegate_user_id"],
            ["users.id"],
            name=op.f("fk_delegated_access_delegate_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by_user_id"],
            ["users.id"],
            name=op.f("fk_delegated_access_invited_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name=op.f("fk_delegated_access_profile_id_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_delegated_access")),
        sa.UniqueConstraint("public_id", name=op.f("uq_delegated_access_public_id")),
    )
    op.create_index(
        "ix_delegated_access_delegate",
        "delegated_access",
        ["delegate_user_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_delegated_access_invited_phone",
        "delegated_access",
        ["invited_phone_e164", "status"],
        unique=False,
    )
    op.create_index(
        "ix_delegated_access_profile", "delegated_access", ["profile_id", "status"], unique=False
    )
    op.create_table(
        "partner_preferences",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("age_min", sa.SmallInteger(), nullable=True),
        sa.Column("age_max", sa.SmallInteger(), nullable=True),
        sa.Column("height_min_cm", sa.SmallInteger(), nullable=True),
        sa.Column("height_max_cm", sa.SmallInteger(), nullable=True),
        sa.Column("marital_statuses", sa.JSON(), nullable=True),
        sa.Column("location_rules", sa.JSON(), nullable=True),
        sa.Column("education_levels", sa.JSON(), nullable=True),
        sa.Column("employment_types", sa.JSON(), nullable=True),
        sa.Column("income_bands", sa.JSON(), nullable=True),
        sa.Column("diets", sa.JSON(), nullable=True),
        sa.Column("mother_tongues", sa.JSON(), nullable=True),
        sa.Column("must_have", sa.JSON(), nullable=True),
        sa.Column("preferred", sa.JSON(), nullable=True),
        sa.Column("excluded", sa.JSON(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", DT, nullable=False),
        sa.Column("updated_at", DT, nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name=op.f("fk_partner_preferences_profile_id_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_partner_preferences")),
        sa.UniqueConstraint("public_id", name=op.f("uq_partner_preferences_public_id")),
    )
    op.create_index(
        op.f("ix_partner_preferences_profile_id"),
        "partner_preferences",
        ["profile_id"],
        unique=False,
    )
    op.create_table(
        "profile_community",
        sa.Column("profile_id", sa.BigInteger(), nullable=False),
        sa.Column("community_id", sa.BigInteger(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(
            ["community_id"],
            ["community_taxonomy.id"],
            name=op.f("fk_profile_community_community_id_community_taxonomy"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name=op.f("fk_profile_community_profile_id_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("profile_id", "community_id", name=op.f("pk_profile_community")),
    )
    op.create_index(
        op.f("ix_profile_community_community_id"),
        "profile_community",
        ["community_id"],
        unique=False,
    )
    op.create_table(
        "profile_education",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("profile_id", sa.BigInteger(), nullable=False),
        sa.Column("qualification", sa.String(length=30), nullable=False),
        sa.Column("field_of_study", sa.String(length=30), nullable=True),
        sa.Column("institution", sa.String(length=150), nullable=True),
        sa.Column("year_completed", sa.SmallInteger(), nullable=True),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name=op.f("fk_profile_education_profile_id_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profile_education")),
        sa.UniqueConstraint("profile_id", name=op.f("uq_profile_education_profile_id")),
    )
    op.create_table(
        "profile_employment",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("profile_id", sa.BigInteger(), nullable=False),
        sa.Column("employment_type", sa.String(length=30), nullable=False),
        sa.Column("occupation", sa.String(length=100), nullable=True),
        sa.Column("industry", sa.String(length=30), nullable=True),
        sa.Column("employer", sa.String(length=150), nullable=True),
        sa.Column("work_city_id", sa.BigInteger(), nullable=True),
        sa.Column("income_band", sa.String(length=20), nullable=True),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name=op.f("fk_profile_employment_profile_id_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["work_city_id"],
            ["locations.id"],
            name=op.f("fk_profile_employment_work_city_id_locations"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profile_employment")),
        sa.UniqueConstraint("profile_id", name=op.f("uq_profile_employment_profile_id")),
    )
    op.create_table(
        "profile_family_details",
        sa.Column("profile_id", sa.BigInteger(), nullable=False),
        sa.Column("family_type", sa.String(length=20), nullable=True),
        sa.Column("family_values", sa.String(length=20), nullable=True),
        sa.Column("native_district_id", sa.BigInteger(), nullable=True),
        sa.Column("father_occupation", sa.String(length=100), nullable=True),
        sa.Column("mother_occupation", sa.String(length=100), nullable=True),
        sa.Column("siblings_count", sa.SmallInteger(), nullable=True),
        sa.Column("siblings_married", sa.SmallInteger(), nullable=True),
        sa.Column("family_description", sa.String(length=1000), nullable=True),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(
            ["native_district_id"],
            ["locations.id"],
            name=op.f("fk_profile_family_details_native_district_id_locations"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name=op.f("fk_profile_family_details_profile_id_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("profile_id", name=op.f("pk_profile_family_details")),
    )
    op.create_table(
        "profile_personal_details",
        sa.Column("profile_id", sa.BigInteger(), nullable=False),
        sa.Column("physical_status", sa.String(length=30), nullable=True),
        sa.Column("languages", sa.JSON(), nullable=True),
        sa.Column("about_me", sa.Text(), nullable=True),
        sa.Column("diet", sa.String(length=20), nullable=True),
        sa.Column("smoking", sa.String(length=20), nullable=True),
        sa.Column("drinking", sa.String(length=20), nullable=True),
        sa.Column("hobbies", sa.JSON(), nullable=True),
        sa.Column("interests", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name=op.f("fk_profile_personal_details_profile_id_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("profile_id", name=op.f("pk_profile_personal_details")),
    )
    op.create_table(
        "profile_photos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("thumbnail_key", sa.String(length=255), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("moderation_status", sa.String(length=20), nullable=False),
        sa.Column("moderation_reason", sa.String(length=50), nullable=True),
        sa.Column("uploaded_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", DT, nullable=False),
        sa.Column("deleted_at", DT, nullable=True),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name=op.f("fk_profile_photos_profile_id_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name=op.f("fk_profile_photos_uploaded_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profile_photos")),
        sa.UniqueConstraint("public_id", name=op.f("uq_profile_photos_public_id")),
    )
    op.create_index(
        op.f("ix_profile_photos_moderation_status"),
        "profile_photos",
        ["moderation_status"],
        unique=False,
    )
    op.create_index(
        "ix_profile_photos_profile",
        "profile_photos",
        ["profile_id", "deleted_at", "sort_order"],
        unique=False,
    )
    op.create_table(
        "profile_status_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("profile_id", sa.BigInteger(), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=False),
        sa.Column("reason_code", sa.String(length=50), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", DT, nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_profile_status_history_actor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name=op.f("fk_profile_status_history_profile_id_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profile_status_history")),
    )
    op.create_index(
        op.f("ix_profile_status_history_profile_id"),
        "profile_status_history",
        ["profile_id"],
        unique=False,
    )
    op.create_table(
        "preference_community_values",
        sa.Column("preference_id", sa.BigInteger(), nullable=False),
        sa.Column("community_id", sa.BigInteger(), nullable=False),
        sa.Column("preference_type", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(
            ["community_id"],
            ["community_taxonomy.id"],
            name=op.f("fk_preference_community_values_community_id_community_taxonomy"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["preference_id"],
            ["partner_preferences.id"],
            name=op.f("fk_preference_community_values_preference_id_partner_preferences"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "preference_id", "community_id", name=op.f("pk_preference_community_values")
        ),
    )

    _seed()


def _seed() -> None:
    loc = sa.table(
        "locations",
        sa.column("id", sa.BigInteger),
        sa.column("parent_id", sa.BigInteger),
        sa.column("type", sa.String),
        sa.column("code", sa.String),
        sa.column("name_en", sa.String),
        sa.column("name_ta", sa.String),
        sa.column("active", sa.Boolean),
    )
    rows: list[dict[str, object]] = []
    next_id = 1

    def add(parent: int | None, type_: str, code: str, en: str, ta: str) -> int:
        nonlocal next_id
        rows.append(
            {
                "id": next_id,
                "parent_id": parent,
                "type": type_,
                "code": code,
                "name_en": en,
                "name_ta": ta,
                "active": True,
            }
        )
        next_id += 1
        return next_id - 1

    country_ids = {code: add(None, "country", code, en, ta) for code, en, ta in COUNTRIES}
    tn = add(country_ids["IN"], "state", "in-tn", "Tamil Nadu", "தமிழ்நாடு")
    for code, en, ta, cities in TN_DISTRICTS:
        district = add(tn, "district", f"tn-{code}", en, ta)
        add(
            district,
            "city",
            f"tn-{code}-city",
            en if code != "nilgiris" else cities[0][1],
            ta if code != "nilgiris" else cities[0][2],
        )
        for city_code, city_en, city_ta in cities if code != "nilgiris" else cities[1:]:
            add(district, "city", f"tn-{city_code}", city_en, city_ta)
    for code, en, ta in OTHER_STATES:
        add(country_ids["IN"], "state", f"in-{code}", en, ta)
    op.bulk_insert(loc, rows)

    tax = sa.table(
        "community_taxonomy",
        sa.column("id", sa.BigInteger),
        sa.column("parent_id", sa.BigInteger),
        sa.column("type", sa.String),
        sa.column("code", sa.String),
        sa.column("label_en", sa.String),
        sa.column("label_ta", sa.String),
        sa.column("active", sa.Boolean),
        sa.column("sort_order", sa.SmallInteger),
    )
    code, en, ta = COMMUNITY
    tax_rows: list[dict[str, object]] = [
        {
            "id": 1,
            "parent_id": None,
            "type": "community",
            "code": code,
            "label_en": en,
            "label_ta": ta,
            "active": True,
            "sort_order": 0,
        }
    ]
    for i, (sub_code, sub_en, sub_ta) in enumerate(SUB_COMMUNITIES, start=2):
        tax_rows.append(
            {
                "id": i,
                "parent_id": 1,
                "type": "sub_community",
                "code": sub_code,
                "label_en": sub_en,
                "label_ta": sub_ta,
                "active": True,
                "sort_order": i,
            }
        )
    op.bulk_insert(tax, tax_rows)


def downgrade() -> None:
    op.drop_table("preference_community_values")
    op.drop_table("profile_status_history")
    op.drop_table("profile_photos")
    op.drop_table("profile_personal_details")
    op.drop_table("profile_family_details")
    op.drop_table("profile_employment")
    op.drop_table("profile_education")
    op.drop_table("profile_community")
    op.drop_table("partner_preferences")
    op.drop_table("delegated_access")
    op.drop_table("profiles")
    op.drop_table("locations")
    op.drop_table("community_taxonomy")
