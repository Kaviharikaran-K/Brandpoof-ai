import asyncio
import datetime as dt
import uuid
from pathlib import Path

from sqlalchemy import select

from app import models
from app.audit import log_audit
from app.config import get_settings
from app.database import SessionLocal
from app.security import hash_password

DEMO_PASSWORD = "Demo1234!"

GUIDELINE_TEXT = """NovaCloud Brand Guidelines
Fictional demo data for the BrandProof AI platform.

Product: NovaCloud by NovaTech Solutions
Tone of voice: professional and friendly.

1. Terminology
- Required term: "Customer". Always refer to the people who buy NovaCloud as customers.
- Prohibited term: "Consumer". Do not use "consumer" in NovaCloud communications.

2. Verified product facts (fictional)
- NovaCloud supports up to 5,000 users per tenant (Product Handbook v2.1).
- NovaCloud availability is 99.5% (Service Level Agreement v1.3).
- NovaCloud support is available 24/7 (Support Policy v4.0).

3. Claims policy
Capacity, availability and support commitments must match the verified facts above.
Never publish promotional promises such as "100%", "guaranteed" or "best" unless a
confirmed approved fact exists for the claim.
"""


async def seed() -> None:
    async with SessionLocal() as db:
        existing = await db.scalar(
            select(models.Organisation).where(models.Organisation.slug == "novatech-solutions")
        )
        if existing is not None:
            print("Demo data already seeded. Nothing to do.")
            return

        admin = models.User(
            email="admin@novatech.demo",
            hashed_password=hash_password(DEMO_PASSWORD),
            full_name="Priya Sharma",
        )
        creator = models.User(
            email="creator@novatech.demo",
            hashed_password=hash_password(DEMO_PASSWORD),
            full_name="Marcus Webb",
        )
        reviewer = models.User(
            email="reviewer@novatech.demo",
            hashed_password=hash_password(DEMO_PASSWORD),
            full_name="Elena Rossi",
        )
        db.add_all([admin, creator, reviewer])
        await db.flush()

        org = models.Organisation(
            name="NovaTech Solutions",
            slug="novatech-solutions",
            demo=True,
        )
        db.add(org)
        await db.flush()

        db.add_all(
            [
                models.OrganisationMember(org_id=org.id, user_id=admin.id, role=models.ROLE_ADMIN),
                models.OrganisationMember(org_id=org.id, user_id=creator.id, role=models.ROLE_CREATOR),
                models.OrganisationMember(org_id=org.id, user_id=reviewer.id, role=models.ROLE_REVIEWER),
            ]
        )

        profile = models.BrandProfile(
            org_id=org.id,
            name="NovaTech Solutions",
            product_name="NovaCloud",
            tagline="Dependable cloud, plainly explained.",
            tone="Professional and friendly",
            description=(
                "Fictional demo brand profile. NovaCloud is the flagship cloud platform of "
                "NovaTech Solutions. All content in this organisation is fictional demo data."
            ),
        )
        db.add(profile)

        facts = [
            models.ApprovedFact(
                org_id=org.id,
                fact_id="NC-FR-001",
                name="Maximum supported users",
                approved_value="5,000",
                description="NovaCloud supports up to 5,000 users per tenant. Fictional demo data.",
                source_ref="NovaCloud Product Handbook v2.1, section 2.4",
                version=2,
                effective_date=dt.date(2025, 1, 1),
                expiry_date=None,
                approval_status=models.FACT_PENDING,
                created_by_id=admin.id,
            ),
            models.ApprovedFact(
                org_id=org.id,
                fact_id="NC-FR-002",
                name="Availability",
                approved_value="99.5%",
                description="NovaCloud availability is 99.5% as defined in the SLA. Fictional demo data.",
                source_ref="NovaCloud Service Level Agreement v1.3",
                version=1,
                effective_date=dt.date(2025, 1, 1),
                expiry_date=None,
                approval_status=models.FACT_PENDING,
                created_by_id=admin.id,
            ),
            models.ApprovedFact(
                org_id=org.id,
                fact_id="NC-FR-003",
                name="Support hours",
                approved_value="24/7",
                description="NovaCloud support is available 24 hours a day, 7 days a week. Fictional demo data.",
                source_ref="NovaCloud Support Policy v4.0",
                version=1,
                effective_date=dt.date(2025, 1, 1),
                expiry_date=None,
                approval_status=models.FACT_PENDING,
                created_by_id=admin.id,
            ),
        ]
        db.add_all(facts)

        terms = [
            models.ApprovedTerm(
                org_id=org.id,
                rule_type=models.RULE_REQUIRED,
                term="Customer",
                description="Required term. Always refer to buyers of NovaCloud as customers. Fictional demo data.",
                created_by_id=admin.id,
            ),
            models.ApprovedTerm(
                org_id=org.id,
                rule_type=models.RULE_PROHIBITED,
                term="Consumer",
                description="Prohibited term. Use 'customer' instead of 'consumer'. Fictional demo data.",
                created_by_id=admin.id,
            ),
        ]
        db.add_all(terms)

        colours = [
            models.ApprovedAsset(
                org_id=org.id,
                asset_type="colour",
                name="Nova Teal",
                colour_value="#0F766E",
                created_by_id=admin.id,
            ),
            models.ApprovedAsset(
                org_id=org.id,
                asset_type="colour",
                name="Nova Navy",
                colour_value="#1B2A4A",
                created_by_id=admin.id,
            ),
            models.ApprovedAsset(
                org_id=org.id,
                asset_type="colour",
                name="Nova Paper",
                colour_value="#F7F5F0",
                created_by_id=admin.id,
            ),
        ]
        db.add_all(colours)

        upload_dir = Path(get_settings().upload_dir) / str(org.id) / "guidelines"
        upload_dir.mkdir(parents=True, exist_ok=True)
        stored = f"{uuid.uuid4().hex}.txt"
        (upload_dir / stored).write_text(GUIDELINE_TEXT, encoding="utf-8")
        guideline = models.BrandGuideline(
            org_id=org.id,
            title="NovaCloud brand guidelines (fictional demo data)",
            file_stored=stored,
            file_name="novacloud-brand-guidelines.txt",
            content_type="text/plain",
            size_bytes=len(GUIDELINE_TEXT.encode("utf-8")),
            uploaded_by_id=admin.id,
        )
        db.add(guideline)
        await db.flush()

        await log_audit(
            db,
            org_id=org.id,
            user_id=admin.id,
            action="organisation.seeded",
            entity_type="organisation",
            entity_id=org.id,
            details={"source": "seed script", "note": "Fictional demo data"},
        )
        await db.commit()

        print("Seeded fictional demo organisation: NovaTech Solutions")
        print("  Org slug: novatech-solutions")
        print("  Login accounts (password for all: %s):" % DEMO_PASSWORD)
        print("    admin   -> admin@novatech.demo   (role: admin)")
        print("    creator -> creator@novatech.demo  (role: creator)")
        print("    reviewer-> reviewer@novatech.demo (role: reviewer)")
        print("  Facts NC-FR-001..003 are seeded as PENDING and await admin confirmation.")


if __name__ == "__main__":
    asyncio.run(seed())
