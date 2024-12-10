import datetime
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import NameOID
from cryptography import x509
import os


def create_certificates(cert_dir):
    os.makedirs(cert_dir, exist_ok=True)
    # create the root CA key
    root_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Ohio"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Dublin"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Self Sign"),
            x509.NameAttribute(NameOID.COMMON_NAME, "Self Sign Root CA"),
        ]
    )
    root_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(root_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(
            # Our certificate will be valid for ~10 years
            datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(days=365 * 10)
        )
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(root_key.public_key()),
            critical=False,
        )
        .sign(root_key, hashes.SHA256())
    )
    with open(os.path.join(cert_dir, "root-ca.pem"), "wb") as f:
        f.write(root_cert.public_bytes(serialization.Encoding.PEM))

    with open(os.path.join(cert_dir, "root-ca-key.pem"), "wb") as f:
        f.write(
            root_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    def create_signed_cert(alt_names, cert_name):
        ee_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
        )
        subject = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Ohio"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Dublin"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Self Sign"),
                x509.NameAttribute(NameOID.COMMON_NAME, cert_name),
            ]
        )
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(root_cert.subject)
            .public_key(ee_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            .not_valid_after(
                # Our cert will be valid for 1 year
                datetime.datetime.now(datetime.timezone.utc)
                + datetime.timedelta(days=365)
            )
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=True,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage(
                    [
                        x509.ExtendedKeyUsageOID.CLIENT_AUTH,
                        x509.ExtendedKeyUsageOID.SERVER_AUTH,
                    ]
                ),
                critical=False,
            )
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(ee_key.public_key()),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(
                    root_cert.extensions.get_extension_for_class(
                        x509.SubjectKeyIdentifier
                    ).value
                ),
                critical=False,
            )
        )
        if alt_names:
            builder.add_extension(
                x509.SubjectAlternativeName(alt_names),
                critical=False,
            )
        ee_cert = builder.sign(root_key, hashes.SHA256())
        with open(os.path.join(cert_dir, f"{cert_name}-cert.pem"), "wb") as f:
            f.write(ee_cert.public_bytes(serialization.Encoding.PEM))
        with open(os.path.join(cert_dir, f"{cert_name}-key.pem"), "wb") as f:
            f.write(
                ee_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

    create_signed_cert(
        [
            x509.DNSName("localhost"),
            x509.DNSName("keycloak"),
        ],
        "keycloak",
    )

    create_signed_cert(
        [
            x509.DNSName("localhost"),
            x509.DNSName("concierge"),
        ],
        "concierge",
    )

    create_signed_cert(
        [
            x509.DNSName("localhost"),
            x509.DNSName("opensearch-node1"),
        ],
        "opensearch-node1",
    )

    create_signed_cert(
        [
            x509.DNSName("localhost"),
            x509.DNSName("opensearch-dashboards"),
        ],
        "opensearch-dashboards",
    )

    create_signed_cert(
        [],
        "opensearch-admin",
    )

    create_signed_cert(
        [x509.DNSName("opensearch-admin-client")],
        "opensearch-admin-client",
    )
