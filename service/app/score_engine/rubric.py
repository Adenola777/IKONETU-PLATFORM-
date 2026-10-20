"""Rubric v3, the lane weights, the league thresholds and the cap.

Rubric v3 follows the IkonetU Data Architecture and Scoring System Specification of March 2026
(Exhibit 01-04), which the owner adopted on 20 October 2026 in place of rubric v2. Its eleven
categories, their maximum points and weights, and each signal's points are copied from the
specification's tables on pages 5 to 16 and 36 to 38. The rubric is mirrored into the
rubric_categories and rubric_signals tables by migration 20261020000002, which rubric_sql.py
generates, so a change here needs that migration regenerated and the tests updated.

Every signal earns all of its points or none, because that is how the specification's tables
give them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Category = Literal[
    "identity", "business", "infrastructure", "team", "financial", "academic", "technical", "operations",
    "traction", "awards", "governance", "media",
]
League = Literal["EARLY", "RISING", "INVESTABLE", "ELITE"]
# How a piece of evidence was verified (TRD, Score engine rule 2). The specification's four
# tiers map onto them: Tier 1 government, Tier 2 source and human_confirmed, Tier 3 human and ai,
# Tier 4 self.
Lane = Literal["government", "source", "ai", "human", "human_confirmed", "self"]
EvidenceStatus = Literal["submitted", "checking", "needs_review", "needs_more", "approved", "rejected", "expired"]
ProductStage = Literal["idea", "mvp", "revenue", "scaling"]
# How a founder shows a signal today, as the owner ruled on 20 October 2026:
# reviewer: a reviewer checks the document or link the specification names.
# statement: a reviewer checks a statement or export in place of the API the specification names.
# judgement: a reviewer judges what the specification would have AI assess.
# link: the founder gives a link and a reviewer checks it, until IkonetU checks it automatically.
# self: the founder states it, and it counts at the self-declared weight without a review.
# later: it needs a provider or an automatic check IkonetU does not have yet, so it cannot be added.
How = Literal["reviewer", "statement", "judgement", "link", "self", "later"]

LANES: tuple[Lane, ...] = ("government", "source", "ai", "human", "human_confirmed", "self")
EVIDENCE_STATUSES: tuple[EvidenceStatus, ...] = (
    "submitted", "checking", "needs_review", "needs_more", "approved", "rejected", "expired",
)
PRODUCT_STAGES: tuple[ProductStage, ...] = ("idea", "mvp", "revenue", "scaling")


@dataclass(frozen=True)
class CategoryDef:
    code: Category
    label: str
    max_points: int
    # The category's share of the 1,000, in per cent.
    weight: int
    # A category that fills the same slot as another. The score counts whichever of the two is higher.
    alternative_to: Category | None = None


@dataclass(frozen=True)
class SignalDef:
    code: str
    category: Category
    label: str
    points: int
    how: How
    # What the founder sends, in one sentence.
    hint: str

    @property
    def offered(self) -> bool:
        return self.how != "later"

    @property
    def expected_lane(self) -> Lane:
        """The lane a founder can get today, used to estimate the next best actions."""
        return "self" if self.how == "self" else "human"


@dataclass(frozen=True)
class Rubric:
    version: str
    categories: tuple[CategoryDef, ...]
    signals: tuple[SignalDef, ...] = field(default_factory=tuple)

    def signal(self, code: str) -> SignalDef | None:
        return next((s for s in self.signals if s.code == code), None)

    def category(self, code: str) -> CategoryDef | None:
        return next((c for c in self.categories if c.code == code), None)


# The specification's tier weights (page 17). Self-declared claims count at 0.60 since the
# owner's ruling of 20 October 2026; rubric v2 gave them nothing (PRD E-6).
LANE_WEIGHT: dict[Lane, float] = {
    "government": 1.0,
    "source": 0.95,
    "ai": 0.85,
    "human": 0.85,
    "human_confirmed": 0.95,
    "self": 0.60,
}

# The specification's tier for each lane, for the monthly record's tier mix.
LANE_TIER: dict[Lane, str] = {
    "government": "T1", "source": "T2", "human_confirmed": "T2", "ai": "T3", "human": "T3", "self": "T4",
}

LEAGUE_THRESHOLDS = {"RISING": 301, "INVESTABLE": 601, "ELITE": 851}

# A venture without approved company registration cannot score above this (PRD S-6).
UNREGISTERED_CAP = 600

# The signal whose approval marks a venture as registered.
REGISTRATION_SIGNAL = "company_registration"

CATEGORIES: tuple[CategoryDef, ...] = (
    CategoryDef("identity", "Identity and Legal Existence", 200, 9),
    CategoryDef("business", "Business Registration and Structure", 250, 11),
    CategoryDef("infrastructure", "Professional Infrastructure", 200, 7),
    CategoryDef("team", "Team and Hiring", 200, 9),
    CategoryDef("financial", "Financial Behaviour and Revenue", 300, 14),
    CategoryDef("academic", "Academic Performance", 150, 6),
    CategoryDef("technical", "Technical Output and Product", 250, 12),
    # The specification gives this pathway a maximum of 250, while its 18 signals add up to 270.
    # The category counts at most its maximum, so the extra 20 points earn nothing more.
    CategoryDef("operations", "Business Operations and Output", 250, 12, alternative_to="technical"),
    CategoryDef("traction", "Venture Traction and Market", 300, 14),
    CategoryDef("awards", "Awards, Recognition and Credibility", 150, 4),
    CategoryDef("governance", "Governance and Compliance", 150, 4),
    CategoryDef("media", "Media Centre and Pitch Assets", 260, 10),
)


def _signals(category: Category, rows: list[tuple[str, str, int, How, str]]) -> tuple[SignalDef, ...]:
    return tuple(SignalDef(code, category, label, points, how, hint) for code, label, points, how, hint in rows)


# Six codes keep their rubric v2 names, because discovery's filters and the SQL checks read them:
# company_registration, government_id, tax_registration, revenue, website_live and press_coverage.
RUBRIC_V3 = Rubric(
    version="v3",
    categories=CATEGORIES,
    signals=(
        *_signals("identity", [
            ("legal_name", "Full legal name", 20, "reviewer", "A photo of your national ID card or passport, showing your full name."),
            ("date_of_birth", "Date of birth", 10, "reviewer", "The same ID, showing your date of birth."),
            ("nationality", "Nationality", 10, "reviewer", "The data page of your passport."),
            ("government_id", "National ID number", 25, "reviewer", "A photo of your NIN slip, Ghana Card or Huduma card."),
            ("face_match", "Biometric face match", 30, "later", "Needs a live selfie check, which IkonetU does not have yet."),
            ("residential_address", "Residential address", 15, "reviewer", "A utility bill or bank statement from the last three months, showing your address."),
            ("phone_verified", "Phone number verified", 10, "later", "Needs a text message check, which IkonetU does not have yet."),
            ("email_verified", "Email verified", 5, "later", "IkonetU will add this automatically."),
            ("passport", "Passport", 15, "reviewer", "A photo of your passport's data page."),
            ("bvn", "BVN or equivalent", 20, "later", "Needs a bank connection, which IkonetU does not have yet."),
            ("student_status", "Proof of student status", 15, "reviewer", "Your student ID card or an enrolment letter."),
            ("next_of_kin", "Next of kin or emergency contact", 5, "self", "Say who your emergency contact is to you, for example your sister. IkonetU does not need their name or number."),
            ("social_presence", "Social media presence", 10, "reviewer", "A link to your own LinkedIn or X profile."),
            ("profile_complete", "Profile completeness", 10, "later", "IkonetU will add this automatically."),
        ]),
        *_signals("business", [
            ("company_registration", "Business name registered", 30, "reviewer", "Your CAC, ORC or BRS certificate."),
            ("registration_number", "Registration number verified", 25, "reviewer", "Your certificate of incorporation, showing the number."),
            ("business_type", "Business type", 15, "reviewer", "Your memorandum and articles, or partnership deed."),
            ("registration_date", "Date of registration", 10, "reviewer", "A registry document showing the date the business was registered."),
            ("directors_listed", "Director and shareholder listing", 20, "reviewer", "Form CAC 7 or the registry's list of directors and shareholders."),
            ("tax_registration", "Tax identification number", 25, "reviewer", "Your TIN or KRA PIN certificate."),
            ("vat_registration", "VAT registration", 20, "reviewer", "Your VAT certificate."),
            ("business_address", "Business address verified", 15, "reviewer", "A utility bill at the business address."),
            ("industry_classification", "Industry classification", 10, "self", "Say which industry the business is in, in your own words."),
            ("operating_licence", "Operating licence", 20, "reviewer", "Your licence, if your sector is regulated."),
            ("annual_returns_filed", "Annual returns filed", 15, "reviewer", "Your latest annual return receipt."),
            ("ip_filings", "Intellectual property filings", 20, "reviewer", "A trademark or patent certificate."),
            ("business_bank_account", "Business bank account", 15, "statement", "A bank letter or statement in the business's name."),
            ("company_domain", "Company website or domain", 10, "link", "The address of the business's website."),
        ]),
        *_signals("infrastructure", [
            ("email_domain", "Professional email domain", 20, "link", "The website address whose domain your business email uses."),
            ("google_workspace", "Google Workspace active", 20, "later", "Needs a Google connection, which IkonetU does not have yet."),
            ("microsoft_365", "Microsoft 365 active", 20, "later", "Needs a Microsoft connection, which IkonetU does not have yet."),
            ("crm_in_use", "CRM system in use", 25, "later", "Needs a CRM connection, which IkonetU does not have yet."),
            ("project_tool", "Project management tool", 15, "later", "Needs a connection to the tool, which IkonetU does not have yet."),
            ("collaboration_platform", "Collaboration platform", 15, "later", "Needs a connection to the platform, which IkonetU does not have yet."),
            ("domain_age", "Custom domain age", 15, "link", "The address of the business's website."),
            ("ssl_active", "SSL certificate active", 10, "link", "The address of the business's website."),
            ("company_social_profiles", "Professional social profiles", 15, "reviewer", "Links to the business's LinkedIn page and other profiles."),
            ("business_phone", "Business phone number", 10, "later", "Needs a text message check, which IkonetU does not have yet."),
            ("cloud_storage", "Cloud storage in use", 15, "later", "Needs a storage connection, which IkonetU does not have yet."),
            ("documentation_maturity", "Documentation maturity", 20, "judgement", "Your pitch deck or one-pager. A reviewer judges how complete it is."),
        ]),
        *_signals("team", [
            ("founder_count", "Founder count", 15, "reviewer", "An ID document for each co-founder."),
            ("founder_background", "Founder background verified", 20, "reviewer", "A link to each founder's LinkedIn profile."),
            ("team_size", "Total team size", 15, "reviewer", "A payroll summary."),
            ("payroll_employees", "Full-time employees on payroll", 25, "reviewer", "A PAYE remittance receipt."),
            ("contractors", "Contractors engaged", 10, "reviewer", "A contractor agreement."),
            ("payroll_consistency", "Payroll consistency, 3 months or more", 20, "statement", "Payroll records for at least the last three months."),
            ("statutory_deductions", "Statutory deductions", 20, "reviewer", "Tax or pension remittance receipts."),
            ("team_diversity", "Team diversity (gender ratio)", 10, "self", "Say how many of the team are women and how many are men."),
            ("advisory_board", "Advisory board members", 15, "reviewer", "An advisory agreement."),
            ("equity_plan", "Employee equity or ESOP plan", 15, "reviewer", "Your ESOP or employee equity agreement."),
            ("key_hire", "Key hire in the last 90 days", 10, "statement", "An employment contract dated in the last 90 days."),
            ("skills_mapping", "Team skills mapping", 15, "later", "Needs GitHub and LinkedIn connections, which IkonetU does not have yet."),
            ("founder_full_time", "Founder full-time commitment", 10, "later", "Needs payroll and calendar data, which IkonetU does not have yet."),
        ]),
        *_signals("financial", [
            ("bank_account", "Bank account linked", 15, "statement", "A bank statement for the account the business uses."),
            ("monthly_inflow", "Monthly inflow average, 6 months", 25, "statement", "Bank statements for the last six months."),
            ("monthly_outflow", "Monthly outflow pattern", 15, "statement", "Bank statements for the last six months."),
            ("revenue", "Revenue identified (recurring)", 30, "reviewer", "Sample invoices or receipts from repeat customers."),
            ("revenue_growth", "Revenue growth trajectory", 15, "statement", "Bank or sales statements that show revenue month by month."),
            ("expense_categorisation", "Expense categorisation", 10, "judgement", "Bank statements. A reviewer judges how clearly the costs can be read."),
            ("reserve_ratio", "Savings or reserve ratio", 15, "statement", "Bank statements that show the balance kept back."),
            ("mobile_money_account", "Mobile money account linked", 15, "statement", "A mobile money statement, such as M-Pesa, MTN MoMo or OPay."),
            ("mobile_money_volume", "Mobile money transaction volume", 20, "statement", "Mobile money statements for the last six months."),
            ("payment_gateway", "Payment gateway active", 20, "statement", "A settlement report from Paystack, Flutterwave or another gateway."),
            ("gateway_volume", "Gateway transaction volume", 20, "statement", "Gateway settlement reports for the last six months."),
            ("billing_system", "Invoice or billing system", 10, "reviewer", "Sample invoices."),
            ("credit_score", "Credit bureau score", 25, "later", "Needs a credit bureau, which IkonetU does not use yet."),
            ("outstanding_credit", "Outstanding loans or credit", 10, "later", "Needs a credit bureau, which IkonetU does not use yet."),
            ("debt_to_income", "Debt-to-income ratio", 15, "later", "Needs credit bureau data, which IkonetU does not use yet."),
            ("tax_payments", "Tax payments detected", 15, "reviewer", "Tax payment receipts."),
            ("insurance", "Insurance coverage", 10, "reviewer", "An insurance certificate."),
            ("audited_accounts", "Audited financial statements", 15, "reviewer", "Audited accounts: a profit and loss statement and balance sheet."),
        ]),
        *_signals("academic", [
            ("university", "University name verified", 10, "reviewer", "An admission letter."),
            ("programme_year", "Programme and year", 10, "reviewer", "Your student ID card."),
            ("grades", "Cumulative GPA or grade", 25, "reviewer", "An official transcript or result sheet."),
            ("programme_relevance", "Programme relevance to the venture", 15, "judgement", "Your transcript. A reviewer judges how the programme relates to the venture."),
            ("academic_awards", "Academic awards or distinctions", 15, "reviewer", "An award certificate."),
            ("publications", "Research publications", 15, "reviewer", "A DOI link or the paper as a PDF."),
            ("online_certifications", "Online certifications", 15, "reviewer", "A certificate from Coursera, edX, Udemy, Google or similar."),
            ("entrepreneurship_course", "Entrepreneurship course completed", 10, "reviewer", "A completion certificate."),
            ("final_project", "Final year project relevance", 15, "judgement", "Your project abstract. A reviewer judges how it relates to the venture."),
            ("conference_talks", "Conference presentations", 10, "reviewer", "The conference programme or a photo."),
            ("academic_reference", "Academic reference letter", 10, "reviewer", "A reference letter as a PDF."),
        ]),
        *_signals("technical", [
            ("github_account", "GitHub account linked", 10, "link", "A link to your GitHub profile."),
            ("repositories", "Total repositories", 10, "link", "A link to your GitHub profile."),
            ("commit_frequency", "Commit frequency", 20, "link", "A link to your GitHub profile."),
            ("commit_consistency", "Commit consistency", 20, "link", "A link to your GitHub profile."),
            ("languages", "Programming languages used", 15, "link", "A link to your GitHub profile."),
            ("code_quality", "Code quality indicators", 15, "link", "A link to a repository with tests or automated checks."),
            ("open_source", "Open source contributions", 10, "link", "A link to your GitHub profile."),
            ("website_live", "Deployed product (live URL)", 25, "link", "The address where the product runs."),
            ("uptime", "Product uptime, 30 days", 15, "later", "IkonetU will check this automatically."),
            ("mobile_app", "Mobile app published", 20, "reviewer", "A link to the app's store page."),
            ("app_downloads", "App download count", 15, "statement", "A screenshot of the store console showing downloads."),
            ("active_users", "User count or active users", 20, "statement", "An export or screenshot from your analytics."),
            ("product_docs", "Product documentation", 10, "link", "A link to the repository's README or docs."),
            ("api_docs", "API documentation", 10, "reviewer", "A link to the API documentation."),
            ("demo_video_technical", "Product demo video", 10, "reviewer", "A YouTube or Loom link to a demo of the product."),
            ("tech_blog", "Technical blog or content", 5, "reviewer", "A link to the blog."),
            ("product_hunt", "Product Hunt launch", 10, "reviewer", "A link to the Product Hunt page."),
            ("cloud_infrastructure", "Cloud infrastructure active", 10, "reviewer", "A cloud billing summary."),
        ]),
        *_signals("operations", [
            ("physical_location", "Physical location verified", 20, "reviewer", "A photo of the shopfront, workshop or farm, with its location."),
            ("business_listing", "Google business profile active", 15, "statement", "A link to the business's Google Maps listing."),
            ("customer_reviews", "Customer reviews and ratings", 15, "statement", "Links to the business's reviews."),
            ("product_catalogue", "Product or service catalogue", 20, "reviewer", "Photos of your products and a price list."),
            ("social_storefront", "Active social media storefront", 15, "statement", "A link to the Instagram or Facebook shop."),
            ("whatsapp_business", "WhatsApp Business account", 10, "statement", "A screenshot of the WhatsApp Business catalogue."),
            ("ecommerce_store", "E-commerce platform active", 20, "statement", "An export from your Jumia, Shopify or other seller dashboard."),
            ("pos_terminal", "POS or payment terminal active", 20, "statement", "A POS statement for at least three months."),
            ("supply_chain", "Supply chain documentation", 15, "reviewer", "Three or more supplier invoices."),
            ("inventory", "Inventory management", 15, "reviewer", "A stock list or inventory spreadsheet."),
            ("deliveries", "Delivery and fulfilment evidence", 10, "reviewer", "Delivery receipts or waybills."),
            ("repeat_customers", "Repeat customer rate", 15, "statement", "Payment records that show returning customers."),
            ("operational_consistency", "Operational consistency, 6 months or more", 20, "statement", "Bank statements for at least six months."),
            ("physical_assets", "Physical asset documentation", 10, "reviewer", "Photos of equipment, vehicles or the workshop."),
            ("quality_certification", "Quality certification or licence", 15, "reviewer", "A NAFDAC, SON, KEBS or similar certificate."),
            ("distribution_agreement", "Franchise or distribution agreement", 10, "reviewer", "The agreement."),
            ("seasonal_pattern", "Seasonal revenue pattern", 10, "judgement", "Twelve months of bank statements. A reviewer judges the seasonal pattern."),
            ("operations_video", "Business operations video", 15, "reviewer", "A YouTube link to a walk-through of the operation."),
        ]),
        *_signals("traction", [
            ("customer_count", "Customer count (verified)", 30, "reviewer", "A customer list with evidence such as receipts."),
            ("monthly_active_users", "Monthly active users", 25, "statement", "An analytics export or screenshot."),
            ("user_growth", "User growth rate, 3 months", 25, "statement", "Analytics for the last three months."),
            ("retention", "Customer retention", 20, "statement", "Analytics that show returning users."),
            ("nps", "Net Promoter Score or CSAT", 15, "reviewer", "Your survey results."),
            ("social_following", "Social media following", 10, "statement", "Links to the business's social profiles."),
            ("social_engagement", "Social engagement rate", 10, "statement", "Screenshots of the profiles' insights."),
            ("press_coverage", "Press or media mentions", 15, "reviewer", "Links to the articles."),
            ("partnerships", "Partnerships signed", 20, "reviewer", "An MOU or partnership agreement."),
            ("letter_of_intent", "Letter of intent from a customer or partner", 25, "reviewer", "The letter as a PDF."),
            ("market_size", "Market size articulated", 10, "judgement", "Your market analysis or deck. A reviewer judges it."),
            ("competitive_analysis", "Competitive analysis completed", 10, "reviewer", "Your competitive analysis."),
            ("deck_quality", "Pitch deck quality", 15, "judgement", "Your pitch deck. A reviewer judges its quality."),
            ("accelerator", "Accelerator or incubator participation", 20, "reviewer", "Your acceptance letter or certificate."),
            ("grants", "Grants received", 25, "reviewer", "The grant award letter."),
            ("prior_funding", "Prior funding received", 20, "reviewer", "A term sheet or investment agreement."),
            ("revenue_multiple", "Revenue multiple", 5, "statement", "Statements that show annual or monthly recurring revenue."),
        ]),
        *_signals("awards", [
            ("competition_wins", "Competition wins", 20, "reviewer", "A winner's certificate."),
            ("hackathons", "Hackathon participation", 15, "reviewer", "A hackathon certificate."),
            ("innovation_award", "Innovation award", 20, "reviewer", "An award certificate."),
            ("fellowship", "Fellowship or scholarship", 20, "reviewer", "The offer letter."),
            ("thought_leadership", "Published thought leadership", 10, "reviewer", "Links to your articles."),
            ("speaking", "Speaking engagement", 15, "reviewer", "The programme or a video link."),
            ("mentor_endorsement", "Mentor endorsement", 20, "reviewer", "An endorsement letter from your mentor."),
            ("industry_association", "Industry association membership", 10, "reviewer", "A membership certificate."),
            ("university_award", "University entrepreneurship award", 10, "reviewer", "An award certificate."),
            ("media_feature", "Media interview or feature", 10, "reviewer", "A link to the interview or feature."),
        ]),
        *_signals("governance", [
            ("board", "Board of directors constituted", 15, "reviewer", "A board resolution."),
            ("board_minutes", "Board meeting minutes", 10, "reviewer", "Minutes of a board meeting."),
            ("annual_returns_current", "Annual returns current", 15, "reviewer", "The latest annual return receipt."),
            ("tax_clearance", "Tax compliance certificate", 20, "reviewer", "Your tax clearance certificate."),
            ("data_protection", "Data protection registered", 15, "reviewer", "Your NDPC, ODPC or DPC registration certificate."),
            ("privacy_policy", "Privacy policy published", 10, "reviewer", "A link to your privacy policy."),
            ("terms_published", "Terms of service published", 10, "reviewer", "A link to your terms."),
            ("aml_policy", "Anti-money laundering policy", 15, "reviewer", "Your AML policy."),
            ("insurance_active", "Insurance coverage active", 10, "reviewer", "An insurance certificate."),
            ("esg_policy", "Environmental or social policy", 10, "reviewer", "Your ESG policy."),
            ("conflict_policy", "Conflict of interest policy", 10, "reviewer", "Your conflict of interest policy."),
            ("whistleblower", "Whistleblower mechanism", 10, "reviewer", "Your whistleblower policy."),
        ]),
        *_signals("media", [
            ("pitch_video", "Elevator pitch video, 60 to 90 seconds", 30, "reviewer", "Your pitch on IkonetU. A reviewer checks it names the problem, the solution, the market and the ask."),
            ("pitch_clarity", "Pitch clarity", 20, "judgement", "Your pitch on IkonetU. A reviewer judges how clear it is."),
            ("demo_video", "Product demo video", 25, "reviewer", "A YouTube or Loom link to a demo of the real product."),
            ("progress_photos", "Progress photo timeline", 15, "reviewer", "At least three dated photos over three months or more."),
            ("team_photo", "Team photo", 10, "reviewer", "A photo of the team."),
            ("workspace_photo", "Office or workspace photo", 10, "reviewer", "A photo of where you work."),
            ("testimonial_video", "Customer testimonial video", 20, "reviewer", "A YouTube link to a customer speaking about the product."),
            ("event_appearance", "Event or conference appearance", 15, "reviewer", "A photo and the event programme."),
            ("media_clips", "Media coverage clips", 15, "reviewer", "A screenshot or link to the coverage."),
            ("social_video", "Social media video content", 10, "statement", "Links to the business's videos on Instagram or TikTok."),
            ("pitch_deck", "Pitch deck", 15, "reviewer", "Your pitch deck as a PDF of up to 20 pages."),
            ("deck_completeness", "Pitch deck completeness", 10, "judgement", "Your pitch deck. A reviewer checks the standard sections."),
            ("one_pager", "One-pager or executive summary", 10, "reviewer", "A summary of up to two pages, as a PDF."),
            ("financial_model", "Financial model", 15, "reviewer", "Your financial model as a PDF."),
            ("brand_assets", "Brand identity assets", 5, "reviewer", "Your logo and brand colours."),
            ("video_consistency", "Video content consistency", 10, "judgement", "Links to your videos. A reviewer judges them together."),
            ("media_engagement", "Media engagement metrics", 10, "statement", "Screenshots of views and watch time."),
            ("media_pack", "Investor-ready media pack", 15, "later", "IkonetU will add this automatically."),
        ]),
    ),
)
