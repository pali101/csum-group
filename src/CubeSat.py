import hashlib, hmac

class CubeSat:
    def __init__(self, initial_token):
        self.token = initial_token

    
    def xor_strings(self, s1, s2):
        """XOR two strings and return the result as a string."""
        # Ensure both strings are of the same length
        if len(s1) != len(s2):
            raise ValueError("Both strings must have the same length")

        # XOR each pair of characters from the two strings
        result = [chr(ord(a) ^ ord(b)) for a, b in zip(s1, s2)]
        
        # Convert the list of characters back into a string
        return ''.join(result)

    def receive_update(self, software_update, transmission_token, set_current_token = False):
        """Receive an update from the ground station."""
        # extracted token = transmission_token XOR hash(software_update, token)
        hmac_obj = hmac.new(self.token.encode(), software_update.encode(), hashlib.sha256)
        expected_token = self.xor_strings(transmission_token, hmac_obj.hexdigest())
        # expected_token = self.xor_strings(transmission_token, hashlib.sha256((software_update + self.token).encode()).hexdigest())
        # Verify the extracted token by checking its hash against the current token
        # if hashlib.sha256(expected_token.encode()).hexdigest() == self.token:
        if hmac.compare_digest(hashlib.sha256(expected_token.encode()).hexdigest(), self.token):
            self.token = expected_token
            # print("Software update is verified")
        else:
            print("Software update is not verified")
            # return software_update
