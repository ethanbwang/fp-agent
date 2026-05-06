import asyncio
import hashlib
import json

from geoip2.database import Reader

from util.db_pool import db_transaction


class Request:
    """Class handling the logging of valid requests to a PostgreSQL database."""

    def __init__(self):
        self.IP_HEADER = "X-Forwarded-For"
        self.HEADER_DELIMITER = ": "
        self.CITY_HEADER = "City"
        self.ASN_HEADER = "ASN"
        self.UNKNOWN_STR = "unknown"
        self.log_request_query = "INSERT INTO public.requests (endpoint, req_type, req_headers, req_body, website_version, req_ts) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP(5)) RETURNING req_id"

        self.city_db = Reader("util/GeoLite2-City.mmdb")
        self.asn_db = Reader("util/GeoLite2-ASN.mmdb")

    def __del__(self):
        self.city_db.close()
        self.asn_db.close()

    def hash_ip(self, ip_val: str) -> str:
        """Returns the hash of an IP address."""
        hash_object = hashlib.sha256(ip_val.encode())
        return hash_object.hexdigest()

    async def anonymize_ip(self, req_headers: str, anonymize: bool = False) -> str:
        """
        Extracts the client IP address from req_headers and replaces it with
        its hash. Adds city and ASN headers if anonymize is False.
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

        if not anonymize:
            try:
                city_res = self.city_db.city(ip_val)
                asn_res = self.asn_db.asn(ip_val)

                headers_list.insert(
                    0,
                    self.CITY_HEADER
                    + self.HEADER_DELIMITER
                    + json.dumps(city_res.to_dict()),
                )
                headers_list.insert(
                    0,
                    self.ASN_HEADER
                    + self.HEADER_DELIMITER
                    + json.dumps(asn_res.to_dict()),
                )

            except:
                headers_list.insert(
                    0, self.CITY_HEADER + self.HEADER_DELIMITER + self.UNKNOWN_STR
                )
                headers_list.insert(
                    0, self.ASN_HEADER + self.HEADER_DELIMITER + self.UNKNOWN_STR
                )

        return "\n".join(headers_list)

    def log_request(
        self,
        endpoint: str,
        req_type: str,
        req_headers: str,
        req_body: str,
        website_version: str,
        anonymize: bool = False,
    ) -> int | None:
        """
        Logs request data to PostgreSQL database.

        Args:
            endpoint (str): Website endpoint requested
            req_type (str): Request type (GET, POST, etc.)
            req_headers (str): Request headers
            req_body (str): Request body
            website_version (str): Website version
            anonymize (bool): Whether to anonymize the IP address and add city
                and ASN headers

        Returns:
            (int | None): Request ID
        """
        req_headers = asyncio.run(self.anonymize_ip(req_headers, anonymize))

        with db_transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                self.log_request_query,
                (endpoint, req_type, req_headers, req_body, website_version),
            )
            row = cur.fetchone()
            cur.close()
            return row[0] if row else None
