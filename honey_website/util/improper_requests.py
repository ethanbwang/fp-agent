import hashlib

from util.db_pool import db_transaction


class ImproperRequest:
    """Class handling the logging of invalid requests to a PostgreSQL database."""

    def __init__(self):
        self.IP_HEADER = "X-Forwarded-For"
        self.HEADER_DELIMITER = ": "

    def hash_ip(self, ip_val):
        """Returns the hash of an IP address."""
        hash_object = hashlib.sha256(ip_val.encode())
        return hash_object.hexdigest()

    async def anonymize_ip(self, req_headers):
        """
        Extracts the client IP address from req_headers and replaces it with
        its hash.
        """
        headers_list = req_headers.split("\n")

        for idx, header_key_val in enumerate(headers_list):
            if self.IP_HEADER in header_key_val:
                ip_idx = idx
                ip_val = header_key_val.split(self.HEADER_DELIMITER)[1]
                break

        headers_list[ip_idx] = (
            self.IP_HEADER + self.HEADER_DELIMITER + self.hash_ip(ip_val)
        )

        return "\n".join(headers_list)

    def log_improper_request(
        self,
        endpoint: str,
        req_type: str,
        req_headers: str,
        req_body: str,
        website_version: str,
    ) -> int | None:
        """
        Logs improper request data to PostgreSQL database.

        Args:
            endpoint (str): Website endpoint requested
            req_type (str): Request type (GET, POST, etc.)
            req_headers (str): Request headers
            req_body (str): Request body
            website_version (str): Website version

        Returns:
            (int | None): Request ID
        """
        with db_transaction() as conn:
            log_improper_request_query = """INSERT INTO public.improper_requests (endpoint, req_type,
            req_headers, req_body, website_version, req_ts) VALUES (%s, %s, %s, %s, %s,
            CURRENT_TIMESTAMP(5)) RETURNING req_id"""
            cur = conn.cursor()
            cur.execute(
                log_improper_request_query,
                (endpoint, req_type, req_headers, req_body, website_version),
            )
            row = cur.fetchone()
            cur.close()
            return row[0] if row else None
