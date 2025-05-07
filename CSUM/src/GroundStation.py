import hashlib, secrets, hmac


class GroundStation:
    def __init__(self, name):
        self.name = name
        self.current_token = None
        self.previous_token = None

    def compute_hash(self, data):
        """Compute a SHA256 hash of given data."""
        return hashlib.sha256(data.encode()).hexdigest()

    def create_hashchain(self, seed, length):
        """Create a hashchain (i.e. series of token) starting from a seed value for a given length."""
        chain = [self.compute_hash(seed)]
        for i in range(length - 1):
            chain.append(self.compute_hash(chain[-1]))
        return chain

    def generate_random_token(self, length):
        """Generate a random token of a provided length."""
        return secrets.token_hex(length)

    def xor_strings(self, s1, s2):
        """XOR two strings and return the result as a string."""
        # Ensure both strings are of the same length
        if len(s1) != len(s2):
            raise ValueError("Both strings must have the same length")

        # XOR each pair of characters from the two strings
        result = [chr(ord(a) ^ ord(b)) for a, b in zip(s1, s2)]

        # Convert the list of characters back into a string
        return "".join(result)

    def send_update(self, software_update):
        """Send a software update to the CubeSat."""
        hmac_obj = hmac.new(
            self.previous_token.encode(), software_update.encode(), hashlib.sha256
        )
        transmission_token = self.xor_strings(self.current_token, hmac_obj.hexdigest())
        # transmission_token = self.xor_strings(self.current_token, hashlib.sha256((software_update + self.previous_token).encode()).hexdigest())
        return transmission_token
