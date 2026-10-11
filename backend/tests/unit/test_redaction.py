"""
Unit tests for SecretRedactor (§8.3).
Tests positive and negative cases for all table-driven detectors and generic entropy assignments.
All secrets constructed dynamically at test runtime to satisfy Rule 11.
"""

import pytest

from app.services.redaction.detectors import shannon_entropy
from app.services.redaction.redactor import SecretRedactor


@pytest.fixture
def redactor() -> SecretRedactor:
    return SecretRedactor()


def test_shannon_entropy_calculation():
    # Empty string
    assert shannon_entropy("") == 0.0
    # Uniform characters: low entropy
    assert shannon_entropy("aaaaaaaa") == 0.0
    # English word: moderate entropy
    assert shannon_entropy("password") < 3.0
    # High-entropy random-like string
    high_ent = "aB3$kL9#mP1@xZ8&"
    assert shannon_entropy(high_ent) >= 3.5


def test_redact_aws_access_key(redactor: SecretRedactor):
    # Dynamically build AWS key: AKIA + 16 characters
    fake_key = "AK" + "IA" + "IOSFODNN7" + "EXAMPLE"
    code = f'AWS_ACCESS_KEY = "{fake_key}"\nprint("Connecting")'

    res = redactor.redact(code)
    assert res.redaction_count == 1
    assert "<REDACTED_SECRET:aws_access_key>" in res.redacted_text
    assert fake_key not in res.redacted_text
    # Line count preserved
    assert len(res.redacted_text.splitlines()) == len(code.splitlines())


def test_aws_negative_case(redactor: SecretRedactor):
    # Not an AWS key: wrong length or characters
    code = 'AWS_KEY = "AKIA123"\nVAL = "ASIA_SHORT"'
    res = redactor.redact(code)
    assert res.redaction_count == 0
    assert res.redacted_text == code


def test_redact_github_token(redactor: SecretRedactor):
    # Dynamically build GitHub token: ghp_ + 36 characters
    fake_gh = "gh" + "p_" + "a" * 36
    code = f'const token = "{fake_gh}";'

    res = redactor.redact(code)
    assert res.redaction_count == 1
    assert "<REDACTED_SECRET:github_token>" in res.redacted_text
    assert fake_gh not in res.redacted_text


def test_redact_gitlab_token(redactor: SecretRedactor):
    fake_gl = "gl" + "pat-" + "x" * 20
    code = f'export GITLAB_TOKEN="{fake_gl}"'

    res = redactor.redact(code)
    assert res.redaction_count == 1
    assert "<REDACTED_SECRET:gitlab_token>" in res.redacted_text


def test_redact_slack_token(redactor: SecretRedactor):
    fake_slack = "xo" + "xb-" + "1234567890" + "abcdef"
    code = f'slack_token = "{fake_slack}"'

    res = redactor.redact(code)
    assert res.redaction_count == 1
    assert "<REDACTED_SECRET:slack_token>" in res.redacted_text


def test_redact_google_api_key(redactor: SecretRedactor):
    fake_gkey = "AI" + "za" + "Sy" + "A" * 33
    code = f'apiKey: "{fake_gkey}"'

    res = redactor.redact(code)
    assert res.redaction_count == 1
    assert "<REDACTED_SECRET:google_api_key>" in res.redacted_text


def test_redact_stripe_key(redactor: SecretRedactor):
    fake_stripe = "sk" + "_live_" + "1234567890abcdef12345678"
    code = f'stripe.api_key = "{fake_stripe}"'

    res = redactor.redact(code)
    assert res.redaction_count == 1
    assert "<REDACTED_SECRET:stripe_key>" in res.redacted_text


def test_redact_openai_key(redactor: SecretRedactor):
    fake_ai = "sk" + "-" + "proj-" + "1234567890abcdef123456"
    code = f'client = OpenAI(api_key="{fake_ai}")'

    res = redactor.redact(code)
    assert res.redaction_count == 1
    assert "<REDACTED_SECRET:openai_anthropic_key>" in res.redacted_text


def test_redact_sendgrid_key(redactor: SecretRedactor):
    fake_sg = "SG" + "." + "A" * 25
    code = f'sg_client = SendGridAPIClient("{fake_sg}")'

    res = redactor.redact(code)
    assert res.redaction_count == 1
    assert "<REDACTED_SECRET:sendgrid_key>" in res.redacted_text


def test_redact_twilio_key(redactor: SecretRedactor):
    fake_tw = "SK" + "a1b2c3d4e5f60718293a4b5c6d7e8f90"
    code = f'twilio_key = "{fake_tw}"'

    res = redactor.redact(code)
    assert res.redaction_count == 1
    assert "<REDACTED_SECRET:twilio_key>" in res.redacted_text


def test_redact_jwt(redactor: SecretRedactor):
    seg1 = "eyJ" + "hbGciOiJIUzI1NiJ9"
    seg2 = "eyJ" + "zdWIiOiIxMjM0NTY3ODkwIn0"
    seg3 = "doz" + "GzV_example_signature_hash123"
    fake_jwt = f"{seg1}.{seg2}.{seg3}"
    code = f'Authorization = "Bearer {fake_jwt}"'

    res = redactor.redact(code)
    assert res.redaction_count == 1
    assert "<REDACTED_SECRET:jwt>" in res.redacted_text


def test_redact_pem_private_key(redactor: SecretRedactor):
    pem_body = "MIIEowIBAAKCAQEA0examplefakekey\n1234567890abcdefghijk\n9876543210zyxwvuts"
    pem_block = f"-----BEGIN RSA PRIVATE KEY-----\n{pem_body}\n-----END RSA PRIVATE KEY-----"
    code = f'# Config\nPRIVATE_KEY = """{pem_block}"""\n# End config\n'

    orig_line_count = len(code.splitlines())
    res = redactor.redact(code)
    assert res.redaction_count == 1
    assert "<REDACTED_SECRET:pem_private_key>" in res.redacted_text
    # Crucial rule: line count must be strictly preserved
    assert len(res.redacted_text.splitlines()) == orig_line_count


def test_redact_connection_string(redactor: SecretRedactor):
    fake_pass = "s3cr3t_p4ss_99"
    conn_str = f"postgres://admin:{fake_pass}@db.prod.internal:5432/main"
    code = f'DATABASE_URL = "{conn_str}"'

    res = redactor.redact(code)
    assert res.redaction_count == 1
    assert "<REDACTED_SECRET:connection_string>" in res.redacted_text
    assert fake_pass not in res.redacted_text
    assert (
        "postgres://admin:<REDACTED_SECRET:connection_string>@db.prod.internal:5432/main"
        in res.redacted_text
    )


def test_redact_generic_high_entropy_secret(redactor: SecretRedactor):
    # Sensitive key + high entropy value >= 8 chars and entropy >= 3.5
    high_ent_val = "K9#m$P2!xL8@vQ4%"
    code = f'api_key = "{high_ent_val}"\n'

    res = redactor.redact(code)
    assert res.redaction_count == 1
    assert "<REDACTED_SECRET:generic_secret>" in res.redacted_text
    assert high_ent_val not in res.redacted_text


def test_generic_placeholder_ignored(redactor: SecretRedactor):
    # Obvious placeholders and low-entropy values must not be redacted
    code = """
password = "changeme"
api_key = "your-api-key"
secret = "${SECRET_KEY}"
token = "xxx"
auth = process.env.AUTH_TOKEN
"""
    res = redactor.redact(code)
    assert res.redaction_count == 0
    assert res.redacted_text == code


def test_clean_code_corpus_zero_redactions(redactor: SecretRedactor):
    # Real ordinary code corpus must produce zero false positives
    clean_code = '''
def calculate_metrics(items: list[int]) -> dict[str, float]:
    """Calculates summary statistics."""
    total = sum(items)
    count = len(items)
    average = total / count if count > 0 else 0.0
    return {
        "total": float(total),
        "count": float(count),
        "average": average,
    }

class DataProcessor:
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size

    def process(self, record: dict) -> bool:
        return bool(record.get("is_valid", False))
'''
    res = redactor.redact(clean_code)
    assert res.redaction_count == 0
    assert res.redacted_text == clean_code
