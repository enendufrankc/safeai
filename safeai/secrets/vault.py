"""HashiCorp Vault secret backend placeholder."""


class VaultSecretBackend:
    def get_secret(self, key: str) -> str:
        raise NotImplementedError("Vault backend is not yet implemented")
