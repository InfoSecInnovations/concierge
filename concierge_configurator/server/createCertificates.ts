import path from "path";
import * as forge from "node-forge";

export default async (certDir: string) => {
	const rootKeys = forge.pki.rsa.generateKeyPair(4096);
	const rootCert = forge.pki.createCertificate();

	rootCert.publicKey = rootKeys.publicKey;
	// serial number doesn't really matter for self signed?
	rootCert.serialNumber = "01";
	rootCert.validity.notBefore = new Date();
	rootCert.validity.notAfter = new Date();
	// CA cert is valid for 10 years
	rootCert.validity.notAfter.setFullYear(
		rootCert.validity.notBefore.getFullYear() + 10,
	);
	const rootIssuer = [
		{
			name: "commonName",
			value: "Self Sign Root CA",
		},
		{
			name: "countryName",
			value: "US",
		},
		{
			name: "stateOrProvinceName",
			value: "Ohio",
		},
		{
			name: "localityName",
			value: "Dublin",
		},
		{
			name: "organizationName",
			value: "Self Sign",
		},
	];
	rootCert.setSubject(rootIssuer);
	rootCert.setIssuer(rootIssuer);
	rootCert.setExtensions([
		{
			name: "basicConstraints",
			cA: true,
		},
		{
			name: "keyUsage",
			keyCertSign: true,
			digitalSignature: true,
			nonRepudiation: true,
			keyEncipherment: true,
			dataEncipherment: true,
		},
		{
			name: "subjectKeyIdentifier",
		},
	]);
	rootCert.sign(rootKeys.privateKey, forge.md.sha256.create());

	await Bun.write(
		path.join(certDir, "root-ca.pem"),
		forge.pki.certificateToPem(rootCert),
	);
	await Bun.write(
		path.join(certDir, "root-ca-key.pem"),
		forge.pki.privateKeyToPem(rootKeys.privateKey),
	);

	const createSignedCert = async (certName: string, altNames?: string[]) => {
		const keys = forge.pki.rsa.generateKeyPair(4096);
		const cert = forge.pki.createCertificate();
		cert.publicKey = keys.publicKey;
		// serial number doesn't really matter for self signed?
		cert.serialNumber = "01";
		cert.validity.notBefore = new Date();
		cert.validity.notAfter = new Date();
		// cert is valid for 1 year
		cert.validity.notAfter.setFullYear(
			cert.validity.notBefore.getFullYear() + 1,
		);
		const attrs = [
			{
				name: "commonName",
				value: certName,
			},
			{
				name: "countryName",
				value: "US",
			},
			{
				name: "stateOrProvinceName",
				value: "Ohio",
			},
			{
				name: "localityName",
				value: "Dublin",
			},
			{
				name: "organizationName",
				value: "Self Sign",
			},
		];
		cert.setSubject(attrs);
		cert.setIssuer(rootCert.subject.attributes);
		const extensions: {}[] = [
			{
				name: "basicConstraints",
				cA: false,
			},
			{
				name: "keyUsage",
				keyCertSign: true,
				digitalSignature: true,
				nonRepudiation: true,
				keyEncipherment: true,
				dataEncipherment: true,
			},
			{
				name: "extKeyUsage",
				serverAuth: true,
				clientAuth: true,
				codeSigning: true,
				emailProtection: true,
				timeStamping: true,
			},
			{
				name: "subjectKeyIdentifier",
			},
			{
				name: "authorityKeyIdentifier",
				keyIdentifier: rootCert.generateSubjectKeyIdentifier().getBytes(),
			},
		];
		if (altNames) {
			extensions.push({
				name: "subjectAltName",
				altNames: altNames.map((altName) => ({
					type: 2, // DNS
					value: altName,
				})),
			});
		}
		cert.setExtensions(extensions);
		cert.sign(rootKeys.privateKey, forge.md.sha256.create());

		await Bun.write(
			path.join(certDir, `${certName}-cert.pem`),
			forge.pki.certificateToPem(cert),
		);
		await Bun.write(
			path.join(certDir, `${certName}-key.pem`),
			forge.pki.privateKeyToPem(keys.privateKey),
		);
	};

	await Promise.all([
		createSignedCert("keycloak", ["localhost", "keycloak"]),
		createSignedCert("concierge", ["localhost", "concierge"]),
		createSignedCert("concierge-web", ["localhost", "concierge-web"]),
		createSignedCert("opensearch-node1", ["localhost", "opensearch-node1"]),
		createSignedCert("opensearch-admin"),
		createSignedCert("opensearch-admin-client", ["opensearch-admin-client"]),
	]);
};
