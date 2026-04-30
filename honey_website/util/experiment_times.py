from util.db_pool import db_transaction


class ExperimentTime:
    """Class handling the logging of experiment times to a PostgreSQL database."""

    def __init__(self):
        self.log_start_query = "INSERT INTO public.experiment_times (website_version, start_req) VALUES (%s, %s) RETURNING exp_id"
        self.log_end_query = "UPDATE public.experiment_times SET end_req = %s, webpage = %s WHERE exp_id = %s RETURNING exp_id"

    def log_start_experiment_time(
        self,
        website_version: str,
        start_req: int,
    ) -> int | None:
        """
        Logs improper request data to PostgreSQL database.

        Args:
            website_version (str): Website version
            start_req (int): Start request ID

        Returns:
            (int | None): Request ID
        """
        with db_transaction() as conn:
            cur = conn.cursor()
            cur.execute(self.log_start_query, (website_version, start_req))
            row = cur.fetchone()
            cur.close()
            return row[0] if row else None

    def log_end_experiment_time(
        self,
        end_req: int,
        webpage: str,
        exp_id: int,
    ) -> int | None:
        """
        Logs end experiment time to PostgreSQL database.

        Args:
            end_req (int): End request ID
            webpage (str): Webpage
            exp_id (int): Experiment ID

        Returns:
            (int | None): Experiment ID
        """
        with db_transaction() as conn:
            cur = conn.cursor()
            cur.execute(self.log_end_query, (end_req, webpage, exp_id))
            row = cur.fetchone()
            cur.close()
            return row[0] if row else None
