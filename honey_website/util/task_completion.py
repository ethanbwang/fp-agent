from util.db_pool import db_transaction
from psycopg2 import sql


class TaskCompletion:
    """Class handling the logging of task completion to a PostgreSQL database."""

    def __init__(self):
        self.valid_tasks = {"forums", "flights", "sort", "shop"}

    def log_task_completion(
        self, name: str, student_id: str, task: str, website_version: str
    ) -> str | None:
        if task not in self.valid_tasks:
            return None

        with db_transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM public.participants WHERE student_id = %s",
                (student_id),
            )
            exists = cur.fetchone() is not None

            if not exists:
                # Insert the base row (if a concurrent insert happens, do nothing).
                cur.execute(
                    """
                    INSERT INTO public.participants (student_id, name, website_version)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (student_id) DO NOTHING
                    RETURNING student_id
                    """,
                    (student_id, name, website_version),
                )

            # Mark the requested task column as completed.
            cur.execute(
                sql.SQL(
                    "UPDATE public.participants SET {} = TRUE WHERE student_id = %s RETURNING student_id"
                ).format(sql.Identifier(task)),
                (student_id),
            )
            row = cur.fetchone()
            cur.close()
            return row[0] if row else None

    def log_task_completion_update(
        self,
        old_student_id: str,
        name: str,
        student_id: str,
        task: str,
        website_version: str,
    ) -> str | None:
        if task not in self.valid_tasks:
            return None

        with db_transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM public.participants WHERE student_id = %s",
                (old_student_id),
            )
            exists = cur.fetchone() is not None

            if not exists:
                # Insert the base row (if a concurrent insert happens, do nothing).
                cur.execute(
                    """
                    INSERT INTO public.participants (student_id, name, website_version)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (student_id) DO NOTHING
                    RETURNING student_id
                    """,
                    (student_id, name, website_version),
                )
            else:
                cur.execute(
                    "UPDATE public.participants SET student_id = %s, name = %s, website_version = %s WHERE student_id = %s RETURNING student_id",
                    (student_id, name, website_version, old_student_id),
                )

            # Mark the requested task column as completed.
            cur.execute(
                sql.SQL(
                    "UPDATE public.participants SET {} = TRUE WHERE student_id = %s RETURNING student_id"
                ).format(sql.Identifier(task)),
                (student_id),
            )
            row = cur.fetchone()
            cur.close()
            return row[0] if row else None
