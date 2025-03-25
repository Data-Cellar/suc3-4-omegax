#!/usr/bin/env bash

set -e

: "${KEYSTORE_PATH:?}"
: "${KEYSTORE_PASSWORD:?}"
: "${OUT_DIR:?}"
: "${PUBKEY_ALIAS:?}"
: "${PRIVKEY_ALIAS:?}"
: "${DOTENV_NAME:?}"

TEMP_DIR=$(mktemp -d)

# Extract the public certificate from the PKCS12 keystore
openssl pkcs12 -in ${KEYSTORE_PATH} -nodes -nokeys -passin pass:${KEYSTORE_PASSWORD} |
    sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' >${TEMP_DIR}/cert.pem

# Extract the private key from the PKCS12 keystore
openssl pkcs12 -in ${KEYSTORE_PATH} -nodes -nocerts -passin pass:${KEYSTORE_PASSWORD} |
    sed -ne '/-BEGIN PRIVATE KEY-/,/-END PRIVATE KEY-/p' >${TEMP_DIR}/key.pem

# Convert PEM to JWK using Node.js
node -e '
const fs = require("fs");
const crypto = require("crypto");

function pemToJwk(pemPath, isPrivate) {
    const pemContent = fs.readFileSync(pemPath, "utf8");
    const key = isPrivate 
        ? crypto.createPrivateKey(pemContent)
        : crypto.createPublicKey(pemContent);
    
    return key.export({ format: "jwk" });
}

// Convert and save public key
const pubJwk = pemToJwk("'${TEMP_DIR}'/cert.pem", false);
fs.writeFileSync("'${TEMP_DIR}'/pub.jwk", 
    `${process.env.PUBKEY_ALIAS}=${JSON.stringify(pubJwk)}\n`);

// Convert and save private key
const privJwk = pemToJwk("'${TEMP_DIR}'/key.pem", true);
fs.writeFileSync("'${TEMP_DIR}'/priv.jwk", 
    `${process.env.PRIVKEY_ALIAS}=${JSON.stringify(privJwk)}\n`);
'

# Combine the public key and private key entries into a single dotenv file
cat ${TEMP_DIR}/pub.jwk ${TEMP_DIR}/priv.jwk >${OUT_DIR}/${DOTENV_NAME}

# Clean up intermediate files
rm ${TEMP_DIR}/cert.pem ${TEMP_DIR}/key.pem ${TEMP_DIR}/pub.jwk ${TEMP_DIR}/priv.jwk
