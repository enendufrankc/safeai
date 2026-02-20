"""AWS Secrets Manager backend placeholder."""


class AWSSecretBackend:
    def get_secret(self, key: str) -> str:
        raise NotImplementedError("AWS Secrets Manager backend is not yet implemented")
