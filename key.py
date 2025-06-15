import secrets
import string

def generate_api_key(length=32, prefix="sk-"):
    """Generate a secure API key"""
    alphabet = string.ascii_letters + string.digits
    key = ''.join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}{key}"

if __name__ == "__main__":
    api_key = generate_api_key()
    print(f"Generated API Key: {api_key}")
    print(f"Set it as environment variable: export API_KEY='{api_key}'")