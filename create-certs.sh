#!/usr/bin/env bash

# Enable verbose execution and exit on error
set -xe

# Check required environment variables
: "${OUT_DIR:?}"
: "${KEY_ALIAS:?}"
: "${KEY_PASSW:?}"

# Default subject if not provided
: "${CERT_SUBJECT:=/C=ES/ST=Asturias/L=Gijon/O=CTIC/OU=CTIC/CN=ctic.es}"

# Generate self-signed certificate and private key
openssl req -x509 \
    -nodes \
    -newkey rsa:4096 \
    -keyout ${OUT_DIR}/key.pem \
    -out ${OUT_DIR}/cert.pem \
    -days 365 \
    -subj "${CERT_SUBJECT}"

# Export certificate and private key to PKCS12 format
openssl pkcs12 -export \
    -in ${OUT_DIR}/cert.pem \
    -inkey ${OUT_DIR}/key.pem \
    -out ${OUT_DIR}/cert.pfx \
    -name ${KEY_ALIAS} \
    -passout pass:${KEY_PASSW}
