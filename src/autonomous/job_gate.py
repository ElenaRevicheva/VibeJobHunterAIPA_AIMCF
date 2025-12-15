from typing import Dict

ROLE_KEYWORDS = {
    "founding",
    "platform",
    "product",
    "automation",
    "infra",
}

MIN_COMPANY_SIZE = 5
MAX_COMPANY_SIZE = 100

ALLOWED_STAGES = {
    "pre-seed",
    "seed",
    "series a",
    "series b",
}

REGIONAL_SALARY_FLOOR = {
    "panama": 45000,
    "remote": 60000,
}


class JobGate:
    """
    HARD career gate.
    If this fails → job is discarded forever.
    """

    @staticmethod
    def passes(job: Dict) -> bool:
        # 1️⃣ Company size
        size = job.get("company_size")
        if not size or not (MIN_COMPANY_SIZE <= size <= MAX_COMPANY_SIZE):
            return False

        # 2️⃣ Funding stage
        stage = (job.get("stage") or "").lower()
        if stage not in ALLOWED_STAGES:
            return False

        # 3️⃣ Role keywords
        title = (job.get("title") or "").lower()
        if not any(keyword in title for keyword in ROLE_KEYWORDS):
            return False

        # 4️⃣ Salary floor
        salary = job.get("salary_min")
        location = (job.get("location") or "").lower()

        if salary is None:
            return False

        if "panama" in location:
            return salary >= REGIONAL_SALARY_FLOOR["panama"]

        if "remote" in location:
            return salary >= REGIONAL_SALARY_FLOOR["remote"]

        return False
