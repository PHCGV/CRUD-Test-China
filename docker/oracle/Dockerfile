# syntax=docker/dockerfile:1.7

ARG ORACLE_BASE_IMAGE=gvenzl/oracle-xe:21-slim
FROM ${ORACLE_BASE_IMAGE}

USER root

# Refresh packages in a local image
RUN set -eux; \
    if command -v microdnf >/dev/null 2>&1; then \
        microdnf -y upgrade --refresh; \
        microdnf clean all; \
    elif command -v dnf >/dev/null 2>&1; then \
        dnf -y upgrade --refresh; \
        dnf clean all; \
    elif command -v yum >/dev/null 2>&1; then \
        yum -y update; \
        yum clean all; \
    else \
        echo "No supported package manager found in base image."; \
        exit 1; \
    fi; \
    rm -rf /var/cache/dnf /var/cache/yum

USER oracle
