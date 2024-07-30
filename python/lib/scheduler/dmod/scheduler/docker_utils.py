from abc import ABC
from docker.models.services import Service
from docker.types import SecretReference


class DockerSecretsUtil(ABC):
    """
    Abstraction for utility that helps managing Docker secrets via an API client object received during initialization.
    """

    @classmethod
    def add_secrets_for_service(cls, service: Service, *secrets):
        """
        Update (or initialize) the list of Docker secrets for the given Docker service with some number of new secret
        references.

        Parameters
        ----------
        service : Service
            The Docker service to be updated

        secrets
            A variable number of ::class:`SecretReference` objects to be added as secrets for the service
        """
        # TODO: integration test
        service_secrets_list = list(service.attrs['Secrets']) if service.attrs['Secrets'] is not None else list()
        for secret in secrets:
            service_secrets_list.append(secret)
        service.update(secrets=service_secrets_list)

    @classmethod
    def remove_secrets_for_service(cls, service: Service, *removing_secrets):
        """
        Remove a number of referenced secrets from the list of secrets for the given Docker service.

        Parameters
        ----------
        service : Service
            The Docker service to be updated.

        removing_secrets
            A variable number of ::class:`SecretReference` objects to be removed from the service.

        Returns
        ----------
        int
            The count of actual secrets that were associated and are now removed.

        """
        # TODO: integration test
        if service.attrs['Secrets'] is None or len(service.attrs['Secrets']) == 0:
            return 0
        count_removed = 0
        service_secrets_list = list()
        for secret in list(service.attrs['Secrets']):
            re_add = True
            for removing_secret in removing_secrets:
                if removing_secret is None:
                    continue
                elif secret['SecretName'] == removing_secret['SecretName']:
                    re_add = False
                    count_removed += 1
                    break
            if re_add:
                service_secrets_list.append(secret)
        service.update(secrets=service_secrets_list)
        return count_removed

    def __init__(self, docker_client):
        self.docker_client = docker_client

    def create_docker_secret(self, name: str, data: bytes) -> SecretReference:
        """
        Create a Docker secret using the client API and return a secret reference object.

        Parameters
        ----------
        name : str
            The name for the secret

        data : bytes
            The secret data

        Returns
        -------
        DockerSecretReference
            A reference object for the created Docker secret
        """
        # TODO: fix the KeyError
        # TODO: unit test (or integration test)
        try:
            self.docker_client.secrets.create(name=name, data=data)
        except KeyError:
            pass
        secret = self.docker_client.secrets.get(name)
        return SecretReference(secret_id=secret.id, secret_name=secret.name)
