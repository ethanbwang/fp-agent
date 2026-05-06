from util.db_pool import db_transaction


class ImproperRequest:
    """Class handling the logging of invalid requests to a PostgreSQL database."""

    def __init__(self):
        self.log_improper_request_query = """INSERT INTO public.improper_requests (endpoint, req_type, req_headers, req_body, website_version, req_ts) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP(5)) RETURNING req_id"""

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
            cur = conn.cursor()
            cur.execute(
                self.log_improper_request_query,
                (endpoint, req_type, req_headers, req_body, website_version),
            )
            row = cur.fetchone()
            cur.close()
            return row[0] if row else None
