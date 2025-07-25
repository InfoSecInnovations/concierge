# Shabti Security and RBAC Features

Shabti can run on a local machine without any security controls, but if you're exposing it to a network it is strongly advised that you enable security to protect your instance. You get the following features:

- **TLS/HTTPS encryption:** connections to Shabti will be encrypted using TLS meaning that they use HTTPS rather than HTTP, preventing malicious actors from viewing the data being sent through the connection.
- **RBAC:** users must have a valid account to use Shabti. The administrator can configure different access levels for different users. Many 3rd party identity providers can be linked to Shabti negating the need to set up separate user accounts if you already have an identity management system in place.

## TLS Certificate Management

During the install process Shabti automatically generates all the certificates required to use TLS encryption. There are what are known as self-signed certificates, meaning they are not registered on the internet and are really only suitable for internal use. By default, most browsers will display an error using this type of certificate as they are not signed by any recognized Certificate Authority. You generally have to expand the error to find the option to proceed anyway. It is generally fine to do this if you're accessing the local machine or a machine on your intranet. It is however possible to add these certificates to your trusted certificates to remove the error.

After installing Shabti you will find a directory called `self_signed_certificates` in the same location as the executable. The file called `root-ca.pem` is the Certificate Authority certificate which has been used to create and sign the other certificates. Depending on your operating system there are different processes to add a certificate to the trusted certificate store. Once you have trusted `root-ca.pem` you should be able to freely access Shabti from your web browser.