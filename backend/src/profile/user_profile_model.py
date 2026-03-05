from typing import Optional, Dict, List, Any
from pydantic import BaseModel, ConfigDict


class UserProfile(BaseModel):
    user_id: Optional[str] = None

    # Location
    state: Optional[str] = None
    district: Optional[str] = None
    pincode: Optional[str] = None

    # Core demographics
    age: Optional[int] = None
    gender: Optional[str] = None           # "male", "female", "other", "unspecified"
    category: Optional[str] = None         # "SC", "ST", "OBC", "EWS", "General", etc.

    # Socio-economic
    income_annual: Optional[float] = None  # in INR
    occupation: Optional[str] = None
    education_level: Optional[str] = None  # e.g. "10th", "12th", "graduate"

    # Agriculture / land
    farmer: Optional[bool] = None
    land_area: Optional[float] = None      # in acres
    land_type: Optional[str] = None

    # Disability / health
    disability: Optional[str] = None       # e.g. "blind", "locomotor", "none"

    # Business / enterprise
    business_type: Optional[str] = None    # e.g. "MSME", "self-employed", "startup"
    enterprise_registered: Optional[bool] = None
    enterprise_registration_number: Optional[str] = None
    enterprise_sector: Optional[str] = None

    # Dates / temporal fields (scheme-related)
    established_date: Optional[str] = None
    effective_date: Optional[str] = None
    date_of_start: Optional[str] = None
    date_of_commencement: Optional[str] = None
    start_date: Optional[str] = None

    # Scheme-specific flags / misc eligibility markers
    registered_with_bocwwb: Optional[bool] = None
    registered_sanitation_worker_child: Optional[bool] = None
    tourism_project_type: Optional[str] = None
    textile_unit_type: Optional[str] = None

    # Generic catch-all for scheme / document flags
    documents: Dict[str, str] = {}         # e.g. {"aadhar": "yes", "caste_certificate": "no"}
    extra_flags: Dict[str, Any] = {}       # for any additional boolean or scalar flags

    model_config = ConfigDict(
        extra="ignore",
        arbitrary_types_allowed=True,
        validate_by_name=True,
        from_attributes=True,
    )
