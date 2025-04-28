import hashlib, hmac, time


class CubeSat:
    def __init__(self, initial_token, shared_secret, id):
        self.token = initial_token
        self.shared_cluster_secret = shared_secret
        self.id = id

    def xor_strings(self, s1, s2):
        """XOR two strings and return the result as a string."""
        # Ensure both strings are of the same length
        if len(s1) != len(s2):
            raise ValueError("Both strings must have the same length")

        # XOR each pair of characters from the two strings
        result = [chr(ord(a) ^ ord(b)) for a, b in zip(s1, s2)]

        # Convert the list of characters back into a string
        return "".join(result)

    def receive_update(
        self, software_update, transmission_token, set_current_token=False
    ):
        """Receive an update from the ground station."""
        # extracted token = transmission_token XOR hash(software_update, token)
        hmac_obj = hmac.new(
            self.token.encode(), software_update.encode(), hashlib.sha256
        )
        expected_token = self.xor_strings(transmission_token, hmac_obj.hexdigest())
        # Verify the extracted token by checking its hash against the current token
        if hmac.compare_digest(
            hashlib.sha256(expected_token.encode()).hexdigest(), self.token
        ):
            self.token = expected_token
            # print(f"[{expected_token[:10]}...] Update verified and accepted.")
            # print("Software update is verified")
        else:
            print("Software update is not verified")
            # return software_update

    def broadcast_update(self, software_update, idrec):
        """Broadcast update received from ground station to CubeSat cluster"""
        ts = int(time.time()) + 5
        message = f"{software_update}|{self.id}|{idrec}|{ts}"
        hmac_obj = hmac.new(
            self.shared_cluster_secret.encode(),
            message.encode(),
            hashlib.sha256,
        )
        authenticated_update_token = hmac_obj.hexdigest()

        # broadcast transmission_token and software_update
        return software_update, authenticated_update_token, self.id, idrec, ts

    def receive_broadcast_update(
        self, software_update, authenticated_update_token, idsen, ts
    ):
        """Verify and accept broadcasted update from another CubeSat."""
        # Check timestamp validity
        if ts < time.time():
            raise ValueError("Token expired")

        message = f"{software_update}|{idsen}|{self.id}|{ts}"
        # Compute expected HMAC to verify authenticity
        hmac_obj = hmac.new(
            self.shared_cluster_secret.encode(),
            message.encode(),
            hashlib.sha256,
        )
        expected_token = hmac_obj.hexdigest()

        # Check if the received token matches the expected token
        if hmac.compare_digest(expected_token, authenticated_update_token):
            # print(f"[{authenticated_update_token[:10]}...] Update verified and accepted.")
            pass
        else:
            print(
                f"[{authenticated_update_token[:10]}...] WARNING: Update verification failed!"
            )
