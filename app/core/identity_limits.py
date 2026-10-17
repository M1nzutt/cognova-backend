def registration_identity_valid(name: str, email: str) -> bool:
    """0003 checks also apply to updates of historical rows; never truncate them."""
    return bool(name.strip() and email.strip() and len(name) <= 30 and len(email) <= 50)
