# Need this extra stage basically to alias the "sources" stage, as there is a
# problem using the current registry (127.0.0.1:5000), apparently due to the ':'
# which Docker thinks is an invalid --from value in the multi-stage copy step
ARG docker_internal_registry
#FROM ${docker_internal_registry}/maas-portal-development
FROM maas-portal-development
COPY ./docker/nwm_gui/migration_service/entrypoint.sh ./
# Set the entry point so that it is run every time the container is started
ENTRYPOINT ["/usr/maas_portal/entrypoint.sh"]
